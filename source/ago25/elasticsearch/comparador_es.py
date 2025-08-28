from elasticsearch import Elasticsearch, helpers
import pandas as pd
import unidecode
import time
from num2words import num2words
import re

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
        " vl ": " vila ",
        " prq ": " parque ",
    }
    texto = " " + texto + " "
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()


def remover_tipo_logradouro(texto):
    """
    Remove tipos de logradouro (RUA, AVENIDA, ALAMEDA...) apenas para comparação textual.
    """
    tipos = ["acesso", "alameda", "avenida", "calcada", "chacara", "condominio", "corredor", "entrada", "escadao", "escadaria", "faixa", "passagem", "praca", "rodovia", "rua", "saida", "serra", "travessa", "travessao", "travessia", "viela"]
    texto = " " + texto.lower() + " "
    for t in tipos:
        texto = texto.replace(f" {t} ", " ")
    return texto.strip()

def numeros_para_texto(texto):
    """
    Substitui números inteiros no texto por palavras.
    Ex: "Rua 22 de Abril" -> "Rua vinte e dois de Abril"
    """
    def substituir(match):
        num = int(match.group())
        return num2words(num, lang='pt')
    
    # Substitui todos os números inteiros
    return re.sub(r'\b\d+\b', substituir, texto)

def montar_endereco(df, colunas, excluir_col_num=None):
    """
    Concatena as colunas que contém as partes do endereço em uma string única
    e aplica normalização de texto e abreviações.
    """
    def concat_normaliza(row):
        partes = []
        for col in colunas:
            if col == excluir_col_num:
                continue
            val = row.get(col, "")
            if pd.isna(val) or str(val).strip() == "":
                val = ""
            else:
                val = str(val)
            partes.append(val)
        texto = " ".join(partes)
        texto = numeros_para_texto(texto)
        texto = normalize(texto)
        texto = normalizar_abreviacoes(texto)
        texto = remover_tipo_logradouro(texto)
        return texto
    return df.apply(concat_normaliza, axis=1)


def montar_bairro(df, coluna):
    """
    Aplica normalização de texto e abreviações na coluna bairro.
    """
    def concat_normaliza(row):
        texto = row.get(coluna, "")
        texto = numeros_para_texto(texto)
        texto = normalize(texto)
        texto = normalizar_abreviacoes(texto)
        texto = remover_tipo_logradouro(texto)
        return texto
    return df.apply(concat_normaliza, axis=1)


def formatar_endereco(row, colunas):
    """
    Monta o endereço original para exibição, concatenando as colunas especificadas,
    exatamente como está na base de dados.
    """
    partes = []
    for col in colunas:
        val = row.get(col, "")
        if pd.isna(val) or str(val).strip() == "":
            partes.append("")
        else:
            partes.append(str(val))
    return " ".join(partes).strip()

def try_int(n):
    """
    Converte valores para inteiro quando possível.
    """
    if pd.isna(n):
        return None
    n_str = str(n).strip()
    if n_str == "":
        return None
    try:
        return int(float(n_str))
    except:
        return None


import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Acessa as variáveis
ELASTICSEARCH_PW = os.getenv("ELASTICSEARCH_PW")

def indexar_enderecos_elasticsearch(df, index_name="enderecos_ref"):
    es = Elasticsearch(
        "https://localhost:9200",
        basic_auth=("elastic", ELASTICSEARCH_PW),
        ca_certs="/etc/elasticsearch/certs/http_ca.crt",
    )

    # Verifica se o Elasticsearch está acessível
    if not es.ping():
        raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
    
    # se existir indice ele deleta para recriar
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, mappings={
        "properties": {
            "endereco_normalizado": {"type": "text"},
            "bairro_normalizado": {"type": "text"},
            "numero": {"type": "long"},
            "original_index": {"type": "integer"}
        }
    })

    actions = [
        {
            "_index": index_name,
            "_id": i,
            "_source": {
                "endereco_normalizado": row["endereco_normalizado"],
                "bairro_normalizado": row["bairro_normalizado"],
                "numero": int(row["NUM_ENDERECO"]),
                "original_index": i
            }
        }
        for i, row in df.iterrows()
    ]

    helpers.bulk(es, actions)
    return es


def buscar_similares_elasticsearch(
    es,
    endereco: str | None,
    bairro: str | None,
    index_name: str,
    numero: str | int | None = None,
    w_endereco: float = 3.0,
    w_bairro: float = 1.0,
    w_numero: float = 0.3,          # peso do número (bônus baixo)
    numero_field: str = "numero",  # CAMPO NUMÉRICO (long)
    gauss_scale: float = 2.0,       # quão “perto” conta muito (≈ metade do bônus em ±scale)
    gauss_decay: float = 0.5,       # quanto decai na distância=scale
    collapse_on_code: bool = True
):
    def _wrap_num_proximity(query, numero_int):
        # Aplica bônus por proximidade do número (gauss)
        return {
            "function_score": {
                "query": query,
                "functions": [
                    {
                        "gauss": {
                            numero_field: {
                                "origin": numero_int,
                                "scale": gauss_scale,
                                "decay": gauss_decay
                            }
                        },
                        "weight": w_numero
                    }
                ],
                "score_mode": "sum",
                "boost_mode": "sum"
            }
        }

    def _search(query, size=1):
        body = {"query": query, "size": size, "track_total_hits": True}
        if collapse_on_code:
            body["collapse"] = {"field": "original_index"}
        return es.search(index=index_name, **body)

    # parse do número para inteiro (só aplica proximidade se der)
    numero_int = None
    if numero is not None:
        try:
            numero_int = int(str(numero).strip())
        except ValueError:
            numero_int = None  # ignora proximidade se não for inteiro

    # --- Tentativa 1: should com boosts individuais ---
    should = []
    if endereco:
        should.append({"match": {"endereco_normalizado": {"query": endereco, "fuzziness": "AUTO", "boost": w_endereco}}})
        should.append({"match_phrase": {"endereco_normalizado": {"query": endereco, "slop": 2, "boost": w_endereco * 0.5}}})
    if bairro:
        should.append({"match": {"bairro_normalizado": {"query": bairro, "fuzziness": "AUTO", "boost": w_bairro}}})

    base_query = {"bool": {"should": should, "minimum_should_match": 1}} if should else {"match_all": {}}
    query1 = _wrap_num_proximity(base_query, numero_int) if numero_int is not None else base_query
    res = _search(query1)
    hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 2: cross_fields (endereco+bairro combinados)
    if not hits and endereco and bairro:
        combined = f"{endereco} {bairro}"
        base2 = {
            "multi_match": {
                "query": combined,
                "type": "cross_fields",
                "fields": [f"endereco_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
                "operator": "OR"
            }
        }
        query2 = _wrap_num_proximity(base2, numero_int) if numero_int is not None else base2
        res = _search(query2)
        hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 3: most_fields (mais permissivo)
    if not hits and (endereco or bairro):
        combined = " ".join([x for x in [endereco, bairro] if x])
        base3 = {
            "multi_match": {
                "query": combined,
                "type": "most_fields",
                "fields": [f"endereco_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
            }
        }
        query3 = _wrap_num_proximity(base3, numero_int) if numero_int is not None else base3
        res = _search(query3)
        hits = res.get("hits", {}).get("hits", [])

    # --- Último recurso: usa match_all mas ainda prioriza número próximo (se houver)
    if not hits:
        base4 = {"match_all": {}}
        query4 = _wrap_num_proximity(base4, numero_int) if numero_int is not None else base4
        res = _search(query4, size=1)
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            return [(None, None, 0.0, None)]
        h = hits[0]; s = h.get("_source", {})
        return [(s.get("endereco_normalizado", ""), s.get("bairro_normalizado", ""), 0.0, s.get("original_index"))]

    # --- Normaliza pelo melhor score
    h0 = hits[0]; s0 = h0.get("_source", {})
    top = (h0.get("_score") or 1.0)
    return [(
        s0.get("endereco_normalizado", ""),
        s0.get("bairro_normalizado", ""),
        (h0.get("_score", 0.0) / top) * 100.0,
        s0.get("original_index"),
    )]


def possivel_bairro_diferente(bairro1, bairro2, score_final, penalizacao=0.95):
    """
    Penaliza o score final se os últimos tokens (possíveis bairros) forem diferentes.
    """
    if bairro1 != bairro2:  # se o último token for diferente -> provável bairro diferente
        return score_final * penalizacao
    return score_final

def comparar_enderecos_es(df1, df2, colunas1, colunas2, coluna_bairro_arquivo1, coluna_bairro_arquivo2,
                          col_num1=None, col_num2=None,
                          peso_texto=0.7, peso_numero=0.3,
                          top_n=5, index_name="enderecos_ref"):
    
    df1 = df1.copy()
    df2 = df2.copy()

    df1["endereco_normalizado"] = montar_endereco(df1, colunas1, excluir_col_num=col_num1)
    df1["bairro_normalizado"] = montar_bairro(df1, coluna_bairro_arquivo1)
    df2["endereco_normalizado"] = montar_endereco(df2, colunas2, excluir_col_num=col_num2)
    df2["bairro_normalizado"] = montar_bairro(df2, coluna_bairro_arquivo2)

    es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
    time.sleep(1)  # Espera para o índice estar pronto

    resultados = []
    # for idx1, endereco1 in df1["endereco_normalizado"].items():
    for idx1, row in df1.iterrows():
        endereco1 = row["endereco_normalizado"]
        bairro1 = row["bairro_normalizado"]

        num1 = df1.loc[idx1, col_num1] if col_num1 else None
        num1_int = try_int(num1)

        similares = buscar_similares_elasticsearch(es, endereco1, bairro1, index_name, num1_int)

        matches_final = []
        
        for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
            num2 = df2.loc[idx2, col_num2] if col_num2 else None
            num2_int = try_int(num2)
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_numero = 100
                else:
                    # Similaridade baseada em quão próximos estão os numeros dos endereços
                    score_numero = max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_numero = None
            if score_numero is None:
                score_final = score_texto_raw
            else:
                score_final = score_texto_raw * peso_texto + score_numero * peso_numero
            score_final = possivel_bairro_diferente(bairro1, bairro2_texto, score_final)
            matches_final.append((idx2, score_texto_raw, score_numero, score_final))
        # Ordena pelo score final
        matches_final.sort(key=lambda x: x[3], reverse=True)
        # Melhor match
        idx2, score_texto, score_numero, melhor_score_final = matches_final[0]
        # Sugestões top N pelo score final
        sugestoes_formatadas = []
        for idx2_sug, score_texto_sug, score_numero_sug, score_final_sug in matches_final[:top_n]:
            endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas2)
            
            # Adiciona o número
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            
            score_final_str = f"{score_final_sug:.0f}" if score_final_sug is not None else "N/A"
            sugestoes_formatadas.append(
                f"{endereco_original} {numero} | Score Final: {score_final_str}"
            )
        
        # Armazena o resultado no DataFrame final
        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
            "bairro_df1": formatar_endereco(df1.loc[idx1], [coluna_bairro_arquivo1]),
            "numero_df1": num1_int,
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(df2.iloc[idx2], colunas2),
            "bairro_df2": formatar_endereco(df2.loc[idx2], [coluna_bairro_arquivo2]),
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
            "similaridade_texto": round(score_texto, 2),
            "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
            "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
            "sugestoes_topN": "; ".join(sugestoes_formatadas),
            "setor_df1": df1.loc[idx1, "CD_SETOR"],
            "setor_df2": df2.loc[idx2, "COD_SETOR"]
        })


    return pd.DataFrame(resultados)
