
import os
import time
from datetime import datetime
from typing import List, Optional, Any
import pandas as pd
import unidecode

# ---- RapidFuzz path: we'll import the user's implementation ----
# Expects comparar_enderecos(df1, df2, colunas1, colunas2, col_num1=None, col_num2=None, limiar_similaridade=85, peso_texto=0.7, peso_numero=0.3, top_n=5)
import comparador as rf_mod

# ---- Elasticsearch implementation (self-contained here) ----
from elasticsearch import Elasticsearch, helpers

def normalize(text):
    if pd.isna(text):
        return ""
    return unidecode.unidecode(str(text)).strip().lower()

def normalizar_abreviacoes(texto):
    abreviacoes = {
        " av ": " avenida ",  
        " avn ": " avenida ",
        " r ": " rua ",
        " pc ": " praca ",
        " al ": " alameda ",
        " tr ": " travessa ",
        " jd ": " jardim ",
        " vl ": " vila "
    }
    texto = " " + texto + " "
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()

def remover_tipo_logradouro(texto):
    tipos = ["rua", "avenida", "alameda", "travessa", "praca", "jardim", "vila"]
    texto = " " + texto.lower() + " "
    for t in tipos:
        texto = texto.replace(f" {t} ", " ")
    return texto.strip()

def montar_endereco(row: pd.Series, colunas: List[str], excluir_col_num: Optional[str] = None) -> str:
    partes = []
    for col in colunas:
        if excluir_col_num is not None and col == excluir_col_num:
            continue
        val = row.get(col, "")
        if pd.isna(val) or str(val).strip() == "":
            val = ""
        else:
            val = str(val)
        partes.append(val)
    texto = " ".join(partes)
    texto = normalize(texto)
    texto = normalizar_abreviacoes(texto)
    texto = remover_tipo_logradouro(texto)
    return texto

def formatar_endereco(row: pd.Series, colunas: List[str]) -> str:
    partes = []
    for col in colunas:
        val = row.get(col, "")
        if pd.isna(val) or str(val).strip() == "":
            partes.append("")
        else:
            partes.append(str(val))
    return " ".join(partes).strip()

def try_int(n: Any) -> Optional[int]:
    if pd.isna(n):
        return None
    n_str = str(n).strip()
    if n_str == "":
        return None
    try:
        return int(float(n_str))
    except Exception:
        return None

class EnderecoESComparator:
    def __init__(self, es: Elasticsearch, index_name: str = "enderecos_ref"):
        self.es = es
        self.index = index_name

    def recreate_index(self):
        if self.es.indices.exists(index=self.index):
            self.es.indices.delete(index=self.index, ignore_unavailable=True)
        body = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "endereco_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "trim"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "endereco_texto": {"type": "text", "analyzer": "endereco_analyzer"},
                    "endereco_normalizado": {"type": "text", "analyzer": "endereco_analyzer"},
                    "numero": {"type": "integer"},
                    "raw": {"type": "keyword"}
                }
            }
        }
        self.es.indices.create(index=self.index, body=body)

    def bulk_index_df2(self, df2: pd.DataFrame, colunas2: List[str], col_num2: Optional[str] = None, chunk_size: int = 2000):
        actions = []
        for i, row in df2.iterrows():
            endereco_original = formatar_endereco(row, colunas2)
            endereco_norm = montar_endereco(row, colunas2, excluir_col_num=col_num2)
            numero = try_int(row.get(col_num2)) if col_num2 else None
            actions.append({
                "_op_type": "index",
                "_index": self.index,
                "_id": i,
                "_source": {
                    "endereco_texto": endereco_original,
                    "endereco_normalizado": endereco_norm,
                    "numero": numero,
                    "raw": endereco_original
                }
            })
            if len(actions) >= chunk_size:
                helpers.bulk(self.es, actions)
                actions = []
        if actions:
            helpers.bulk(self.es, actions)
        self.es.indices.refresh(index=self.index)

    def buscar_matches_para_df1(
        self,
        df1: pd.DataFrame,
        colunas1: List[str],
        col_num1: Optional[str] = None,
        peso_texto: float = 0.7,
        peso_numero: float = 0.3,
        top_n: int = 5,
        max_candidates: int = 200
    ) -> pd.DataFrame:
        resultados = []
        for idx1, row in df1.iterrows():
            endereco_original_1 = formatar_endereco(row, colunas1)
            endereco_norm_1 = montar_endereco(row, colunas1, excluir_col_num=col_num1)
            num1 = try_int(row.get(col_num1)) if col_num1 else None

            query = {
                "size": max_candidates,
                "query": {
                    "script_score": {
                        "query": {
                            "multi_match": {
                                "query": endereco_norm_1 if endereco_norm_1 else endereco_original_1,
                                "fields": ["endereco_normalizado^2", "endereco_texto"],
                                "fuzziness": "AUTO",
                                "operator": "and"
                            }
                        },
                        "script": {
                            "source": """
                                double textScore = _score;
                                double numScore = 0.0;
                                if (params.containsKey('n1') && params.n1 != null && !doc['numero'].empty && doc['numero'].size() > 0) {
                                    double n1 = params.n1;
                                    double n2 = doc['numero'].value;
                                    double diff = Math.abs(n1 - n2);
                                    double maxn = Math.max(n1, n2);
                                    if (maxn > 0) {
                                        numScore = Math.max(0, 1 - (diff / maxn));
                                    } else {
                                        numScore = 0.0;
                                    }
                                }
                                double textPart = params.wt * Math.log(1.0 + textScore);
                                double numPart = params.wn * (numScore * 10.0);
                                return textPart + numPart;
                            """,
                            "params": {
                                "n1": num1,
                                "wt": float(peso_texto),
                                "wn": float(peso_numero)
                            }
                        }
                    }
                }
            }

            resp = self.es.search(index=self.index, body=query)
            hits = resp.get("hits", {}).get("hits", [])

            sugestoes = []
            for h in hits[:top_n]:
                src = h["_source"]
                sugestoes.append(f"{src.get('raw','')} {src.get('numero','')} | Score ES: {h.get('_score',0):.2f}")
            melhor = hits[0] if hits else None

            if melhor is not None:
                src = melhor["_source"]
                idx2 = melhor.get("_id")
                similaridade_final = round(float(melhor.get("_score", 0.0)) * 10.0, 2)
                resultados.append({
                    "idx_df1": idx1,
                    "endereco_df1": endereco_original_1,
                    "numero_df1": num1,
                    "idx_df2": idx2,
                    "endereco_df2": src.get("raw"),
                    "numero_df2": src.get("numero"),
                    "similaridade_texto": None,
                    "similaridade_numero": None,
                    "similaridade_final": similaridade_final,
                    "sugestoes_topN": "; ".join(sugestoes)
                })
            else:
                resultados.append({
                    "idx_df1": idx1,
                    "endereco_df1": endereco_original_1,
                    "numero_df1": num1,
                    "idx_df2": None,
                    "endereco_df2": None,
                    "numero_df2": None,
                    "similaridade_texto": None,
                    "similaridade_numero": None,
                    "similaridade_final": None,
                    "sugestoes_topN": ""
                })

        return pd.DataFrame(resultados)

# ---- funcoes high-level ----

def rodar_rapidfuzz(df1, df2, colunas1, colunas2, col_num1=None, col_num2=None,
                    limiar_similaridade=85, peso_texto=0.7, peso_numero=0.3, top_n=5):
    t0 = time.time()
    df_res = rf_mod.comparar_enderecos(
        df1=df1, df2=df2,
        colunas1=colunas1, colunas2=colunas2,
        col_num1=col_num1, col_num2=col_num2,
        limiar_similaridade=limiar_similaridade,
        peso_texto=peso_texto, peso_numero=peso_numero,
        top_n=top_n
    )
    elapsed = time.time() - t0
    return df_res, elapsed

def rodar_elasticsearch(df1, df2, colunas1, colunas2, col_num1=None, col_num2=None,
                        peso_texto=0.7, peso_numero=0.3, top_n=5, max_candidates=200,
                        index_name="enderecos_ref_unificado"):
    ES_URL = os.getenv("ES_URL", "http://localhost:9200")
    ES_USER = os.getenv("ES_USER")
    ES_PASS = os.getenv("ES_PASS")

    if ES_USER and ES_PASS:
        es = Elasticsearch(ES_URL, basic_auth=(ES_USER, ES_PASS))
    else:
        es = Elasticsearch(ES_URL)

    comp = EnderecoESComparator(es, index_name=index_name)
    t0 = time.time()
    comp.recreate_index()
    comp.bulk_index_df2(df2, colunas2, col_num2=col_num2)
    df_res = comp.buscar_matches_para_df1(
        df1, colunas1=colunas1, col_num1=col_num1,
        peso_texto=peso_texto, peso_numero=peso_numero,
        top_n=top_n, max_candidates=max_candidates
    )
    elapsed = time.time() - t0
    return df_res, elapsed

# ---- executável ----

if __name__ == "__main__":
    # Ajuste aqui os arquivos e colunas
    arquivo1 = "cnes_geo_padrao_ouro_diadema.csv"
    arquivo2 = "3513801_DIADEMA.csv"

    colunas_arquivo1 = ["NO_LOGRADO", "NO_BAIRRO"]
    colunas_arquivo2 = ["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR", "DSC_LOCALIDADE"]

    coluna_numero_arquivo1 = "NU_ENDEREC"
    coluna_numero_arquivo2 = "NUM_ENDERECO"

    df1 = pd.read_csv(arquivo1, sep=";", dtype=str)
    df2 = pd.read_csv(arquivo2, sep=";", dtype=str)

    # Extrai número para colunas auxiliares (evita mudar nomes originais)
    def conv(v):
        try:
            return int(str(v).strip())
        except Exception:
            return None

    df1["numero_logradouro"] = df1[coluna_numero_arquivo1].apply(conv)
    df2["numero_logradouro"] = df2[coluna_numero_arquivo2].apply(conv)

    # ---- RapidFuzz ----
    rf_df, rf_time = rodar_rapidfuzz(
        df1, df2,
        colunas1=colunas_arquivo1,
        colunas2=colunas_arquivo2,
        col_num1="numero_logradouro",
        col_num2="numero_logradouro",
        limiar_similaridade=85,
        peso_texto=0.7, peso_numero=0.3,
        top_n=20
    )

    # ---- Elasticsearch ----
    es_df, es_time = rodar_elasticsearch(
        df1, df2,
        colunas1=colunas_arquivo1,
        colunas2=colunas_arquivo2,
        col_num1="numero_logradouro",
        col_num2="numero_logradouro",
        peso_texto=0.9, peso_numero=0.1,
        top_n=20, max_candidates=300,
        index_name="enderecos_ref_unificado"
    )

    # ---- Exporta ----
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_rf = f"result_rapidfuzz_{ts}.csv"
    out_es = f"result_elasticsearch_{ts}.csv"

    rf_df.to_csv(out_rf, sep=";", decimal=",", index=False)
    es_df.to_csv(out_es, sep=";", decimal=",", index=False)

    print(f"Arquivos salvos: {out_rf} e {out_es}")
    print(f"Tempo RapidFuzz: {rf_time:.2f}s | Tempo Elasticsearch: {es_time:.2f}s")
