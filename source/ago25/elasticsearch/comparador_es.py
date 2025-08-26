# from elasticsearch import Elasticsearch, helpers
# import pandas as pd
# import unidecode
# import time

# def normalize(text):
#     if pd.isna(text):
#         return ""
#     return unidecode.unidecode(str(text)).strip().lower()


# def normalizar_abreviacoes(texto):
#     abreviacoes = {
#         " av ": " avenida ",  
#         " avn ": " avenida ",
#         " r ": " rua ",
#         " pc ": " praca ",
#         " al ": " alameda ",
#         " tr ": " travessa ",
#         " jd ": " jardim ",
#         " vl ": " vila "
#     }
#     texto = " " + texto + " "
#     for abrev, completo in abreviacoes.items():
#         texto = texto.replace(abrev, completo)
#     return texto.strip()


# def remover_tipo_logradouro(texto):
#     tipos = ["rua", "avenida", "alameda", "travessa", "praca", "jardim", "vila"]
#     texto = " " + texto.lower() + " "
#     for t in tipos:
#         texto = texto.replace(f" {t} ", " ")
#     return texto.strip()


# def montar_endereco(df, colunas, excluir_col_num=None):
#     def concat_normaliza(row):
#         partes = []
#         for col in colunas:
#             if col == excluir_col_num:
#                 continue
#             val = row.get(col, "")
#             if pd.isna(val) or str(val).strip() == "":
#                 val = ""
#             partes.append(str(val))
#         texto = " ".join(partes)
#         texto = normalize(texto)
#         texto = normalizar_abreviacoes(texto)
#         texto = remover_tipo_logradouro(texto)
#         return texto
#     return df.apply(concat_normaliza, axis=1)


# def formatar_endereco(row, colunas):
#     return " ".join([str(row.get(col, "") or "") for col in colunas]).strip()


# def try_int(n):
#     if pd.isna(n): return None
#     try: return int(float(str(n).strip()))
#     except: return None


# import os
# from dotenv import load_dotenv

# # Carrega as variáveis do arquivo .env
# load_dotenv()

# # Acessa as variáveis
# ELASTICSEARCH_PW = os.getenv("ELASTICSEARCH_PW")


# def indexar_enderecos_elasticsearch(df, index_name="enderecos_ref"):
#     es = Elasticsearch(
#         "https://localhost:9200",
#         basic_auth=("elastic", ELASTICSEARCH_PW),
#         ca_certs="/etc/elasticsearch/certs/http_ca.crt",
#     )

#     # es = Elasticsearch("http://localhost:9200")

#     # Verifica se o Elasticsearch está acessível
#     if not es.ping():
#         raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
    
#     if es.indices.exists(index=index_name):
#         es.indices.delete(index=index_name)

#     es.indices.create(index=index_name, mappings={
#         "properties": {
#             "endereco_normalizado": {"type": "text"},
#             "original_index": {"type": "integer"}
#         }
#     })

#     actions = [
#         {
#             "_index": index_name,
#             "_id": i,
#             "_source": {
#                 "endereco_normalizado": row["endereco_normalizado"],
#                 "original_index": i
#             }
#         }
#         for i, row in df.iterrows()
#     ]

#     helpers.bulk(es, actions)
#     return es


# def buscar_similares_elasticsearch(es, endereco, index_name, size=100):
#     query = {
#         "query": {
#             "match": {
#                 "endereco_normalizado": {
#                     "query": endereco,
#                     "fuzziness": "AUTO"
#                 }
#             }
#         }
#     }
#     res = es.search(index=index_name, body=query, size=size)
#     return [(hit["_source"]["original_index"], hit["_score"]) for hit in res["hits"]["hits"]]


# def comparar_enderecos_es(df1, df2, colunas1, colunas2,
#                           col_num1=None, col_num2=None,
#                           peso_texto=0.7, peso_numero=0.3,
#                           top_n=5, index_name="enderecos_ref"):
    
#     df1 = df1.copy()
#     df2 = df2.copy()

#     df1["endereco_normalizado"] = montar_endereco(df1, colunas1, excluir_col_num=col_num1)
#     df2["endereco_normalizado"] = montar_endereco(df2, colunas2, excluir_col_num=col_num2)

#     es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
#     time.sleep(1)  # Espera para o índice estar pronto

#     resultados = []

#     for idx1, endereco1 in df1["endereco_normalizado"].items():
#         num1 = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
#         similares = buscar_similares_elasticsearch(es, endereco1, index_name)

#         matches_final = []
#         for idx2, score_texto_raw in similares:
#             num2 = try_int(df2.loc[idx2, col_num2]) if col_num2 else None

#             if num1 is not None and num2 is not None:
#                 diff = abs(num1 - num2)
#                 score_numero = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1, num2)))
#             else:
#                 score_numero = None

#             if score_numero is None:
#                 score_final = score_texto_raw
#             else:
#                 score_final = score_texto_raw * peso_texto + score_numero * peso_numero

#             matches_final.append((idx2, score_texto_raw, score_numero, score_final))

#         matches_final.sort(key=lambda x: x[3], reverse=True)
#         idx2, score_texto, score_numero, melhor_score = matches_final[0] if matches_final else (None, 0, None, 0)

#         sugestoes = []
#         for idx2_sug, st, sn, sf in matches_final[:top_n]:
#             sugestoes.append(
#                 f"{formatar_endereco(df2.loc[idx2_sug], colunas2)} {df2.loc[idx2_sug, col_num2] if col_num2 else ''} | Score Final: {sf:.0f}"
#             )

#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
#             "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.loc[idx2], colunas2) if idx2 is not None else None,
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 and idx2 is not None else None,
#             "similaridade_texto": round(score_texto, 2),
#             "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
#             "similaridade_final": round(melhor_score, 2),
#             "sugestoes_topN": "; ".join(sugestoes)
#         })

#     return pd.DataFrame(resultados)

# comparador_es.py
# import pandas as pd
# import unidecode
# from num2words import num2words
# import re
# from typing import List, Optional, Tuple
# from elasticsearch import Elasticsearch, helpers


# # =========================
# # === Normalização base ===
# # =========================

# def normalize(text):
#     """
#     Remove acentos, coloca tudo em minúsculas e tira espaços extras
#     """
#     if pd.isna(text):
#         return ""
#     return unidecode.unidecode(str(text)).strip().lower()

# def normalizar_abreviacoes(texto):
#     """
#     Substitui abreviações comuns de logradouros para forma completa
#     """
#     abreviacoes = {
#         " av ": " avenida ",
#         " avn ": " avenida ",
#         " r ": " rua ",
#         " pc ": " praca ",
#         " al ": " alameda ",
#         " tr ": " travessa ",
#         " jd ": " jardim ",
#         " vl ": " vila "
#     }
#     texto = " " + texto + " "
#     for abrev, completo in abreviacoes.items():
#         texto = texto.replace(abrev, completo)
#     return texto.strip()

# def numeros_para_texto(texto):
#     """
#     Substitui números inteiros no texto por palavras (pt).
#     Ex: "Rua 22 de Abril" -> "Rua vinte e dois de Abril"
#     """
#     def substituir(match):
#         num = int(match.group())
#         return num2words(num, lang='pt')
#     return re.sub(r'\b\d+\b', substituir, texto)

# def remover_tipo_logradouro(texto):
#     """
#     Remove tipos de logradouro (RUA, AVENIDA, ALAMEDA...) apenas para comparação textual.
#     """
#     tipos = [
#         "acesso","alameda","avenida","calcada","chacara","condominio","corredor",
#         "entrada","escadao","escadaria","faixa","passagem","praca","rodovia","rua",
#         "saida","serra","travessa","travessao","travessia","viela"
#     ]
#     texto = " " + texto.lower() + " "
#     for t in tipos:
#         texto = texto.replace(f" {t} ", " ")
#     return texto.strip()

# def montar_endereco(df, colunas: List[str], excluir_col_num: Optional[str] = None):
#     """
#     Concatena as colunas do endereço, normaliza e aplica as mesmas regras do arquivo original.
#     """
#     def concat_normaliza(row):
#         partes = []
#         for col in colunas:
#             if col == excluir_col_num:
#                 continue
#             val = row.get(col, "")
#             if pd.isna(val) or str(val).strip() == "":
#                 val = ""
#             else:
#                 val = str(val)
#             partes.append(val)
#         texto = " ".join(partes)
#         texto = numeros_para_texto(texto)
#         texto = normalize(texto)
#         texto = normalizar_abreviacoes(texto)
#         texto = remover_tipo_logradouro(texto)
#         return texto
#     return df.apply(concat_normaliza, axis=1)

# def formatar_endereco(row, colunas: List[str]):
#     """
#     Monta o endereço original para exibição.
#     """
#     partes = []
#     for col in colunas:
#         val = row.get(col, "")
#         if pd.isna(val) or str(val).strip() == "":
#             partes.append("")
#         else:
#             partes.append(str(val))
#     return " ".join(partes).strip()

# def possivel_bairro_diferente(end1: str, end2: str, score_final: float, penalizacao: float = 0.95):
#     """
#     Penaliza se últimos tokens forem diferentes (possível bairro).
#     """
#     tokens1 = end1.split()
#     tokens2 = end2.split()
#     if tokens1 and tokens2:
#         ult1, ult2 = tokens1[-1], tokens2[-1]
#         if ult1 != ult2:
#             return score_final * penalizacao
#     return score_final

# def try_int(n):
#     """
#     Converte valores para inteiro quando possível.
#     """
#     if pd.isna(n):
#         return None
#     n_str = str(n).strip()
#     if n_str == "":
#         return None
#     try:
#         return int(float(n_str))
#     except:
#         return None


# # ==================================
# # === Conexão e índice no Elastic ===
# # ==================================

# import os
# from dotenv import load_dotenv

# # Carrega as variáveis do arquivo .env
# load_dotenv()

# # Acessa as variáveis
# ELASTICSEARCH_PW = os.getenv("ELASTICSEARCH_PW")

# def get_es(
#     url: str = "https://localhost:9200",
#     username: str = "elastic",
#     password: str = ELASTICSEARCH_PW,
#     ca_certs: Optional[str] = "/etc/elasticsearch/certs/http_ca.crt",
# ) -> Elasticsearch:
#     """
#     Cria cliente Elasticsearch. Ajuste auth/SSL conforme seu ambiente.
#     """
#     kwargs = dict(
#         basic_auth=(username, password),
#         request_timeout=60,
#         verify_certs=True,
#     )
#     if ca_certs:
#         kwargs["ca_certs"] = ca_certs
#     return Elasticsearch(url, **kwargs)


# def recreate_index(es: Elasticsearch, index_name: str = "enderecos_ref"):
#     """
#     Recria o índice com um analisador simples porém efetivo para PT-BR sem acentos.
#     """
#     if es.indices.exists(index=index_name):
#         es.indices.delete(index=index_name)

#     body = {
#         "settings": {
#             "index": {
#                 "number_of_shards": 1,
#                 "number_of_replicas": 0,
#             },
#             "analysis": {
#                 "analyzer": {
#                     "pt_normalized": {
#                         "type": "custom",
#                         "tokenizer": "standard",
#                         "filter": ["lowercase", "asciifolding"]
#                     }
#                 }
#             }
#         },
#         "mappings": {
#             "properties": {
#                 "endereco_original": {"type": "keyword"},
#                 "endereco_normalizado": {
#                     "type": "text",
#                     "analyzer": "pt_normalized",
#                 },
#                 "numero": {"type": "integer", "ignore_malformed": True},
#             }
#         }
#     }
#     es.indices.create(index=index_name, body=body)


# def bulk_index_df2(
#     es: Elasticsearch,
#     df2: pd.DataFrame,
#     colunas2: List[str],
#     col_num2: Optional[str],
#     index_name: str = "enderecos_ref",
#     chunk_size: int = 2000
# ):
#     """
#     Indexa o df2 como base de referência no Elasticsearch.
#     """
#     df2_local = df2.copy()
#     df2_local["endereco_normalizado"] = montar_endereco(df2_local, colunas2, excluir_col_num=col_num2)

#     def gen_actions():
#         for i, row in df2_local.iterrows():
#             numero = row.get(col_num2, None) if col_num2 else None
#             yield {
#                 "_index": index_name,
#                 "_id": i,  # preserva índice do df2 para referência
#                 "_source": {
#                     "endereco_original": formatar_endereco(row, colunas2),
#                     "endereco_normalizado": row["endereco_normalizado"],
#                     "numero": try_int(numero),
#                 }
#             }

#     helpers.bulk(es, gen_actions(), chunk_size=chunk_size, request_timeout=120)


# # ===================================
# # === Busca e comparação via ES  ====
# # ===================================

# def _query_candidates(
#     es: Elasticsearch,
#     index_name: str,
#     endereco_normalizado: str,
#     size: int = 50
# ) -> List[Tuple[int, str, Optional[int], float]]:
#     """
#     Busca candidatos por match com fuzziness AUTO em endereco_normalizado.
#     Retorna lista: [(id_df2, endereco_normalizado, numero, score_es), ...]
#     """
#     q = {
#         "size": size,
#         "query": {
#             "match": {
#                 "endereco_normalizado": {
#                     "query": endereco_normalizado,
#                     "fuzziness": "AUTO",
#                     "operator": "and"
#                 }
#             }
#         },
#         "_source": ["endereco_normalizado", "numero"]
#     }
#     resp = es.search(index=index_name, body=q)
#     hits = resp.get("hits", {}).get("hits", [])
#     result = []
#     for h in hits:
#         _id = h.get("_id")
#         try:
#             idx2 = int(_id)
#         except:
#             # Se _id não é numérico, guarde assim mesmo (ou mapeie em separado)
#             continue
#         src = h.get("_source", {})
#         result.append(
#             (
#                 idx2,
#                 src.get("endereco_normalizado", ""),
#                 src.get("numero", None),
#                 float(h.get("_score", 0.0))
#             )
#         )
#     return result


# def comparar_enderecos_es(
#     df1: pd.DataFrame,
#     df2: pd.DataFrame,
#     colunas1: List[str],
#     colunas2: List[str],
#     col_num1: Optional[str] = None,
#     col_num2: Optional[str] = None,
#     es: Optional[Elasticsearch] = None,
#     index_name: str = "enderecos_ref",
#     limiar_similaridade: int = 85,     # não é usado para filtrar hard, mas você pode aproveitar
#     peso_texto: float = 0.7,
#     peso_numero: float = 0.3,
#     top_n: int = 5,
#     candidates_size: int = 50
# ) -> pd.DataFrame:
#     """
#     Versão com Elasticsearch:
#     - Indexa df2 (recriando índice).
#     - Para cada linha de df1, busca por fuzzy match e reordena candidatos pelo score final (texto+número).
#     """

#     # 1) Preparar ES (se não informado)
#     _es = es or get_es()
#     recreate_index(_es, index_name=index_name)
#     bulk_index_df2(_es, df2, colunas2, col_num2, index_name=index_name)

#     # 2) Preparar colunas normalizadas
#     df1_local = df1.copy()
#     df1_local["endereco_normalizado"] = montar_endereco(df1_local, colunas1, excluir_col_num=col_num1)

#     resultados = []

#     for idx1, end1_norm in df1_local["endereco_normalizado"].items():
#         # Para exibição:
#         end1_original = formatar_endereco(df1_local.loc[idx1], colunas1)
#         num1 = df1_local.loc[idx1, col_num1] if col_num1 else None
#         num1_int = try_int(num1)

#         # 3) Buscar candidatos no ES
#         candidatos = _query_candidates(_es, index_name, end1_norm, size=candidates_size)

#         # Se não vier nenhum candidato via ES, continue com resultado vazio
#         if not candidatos:
#             resultados.append({
#                 "idx_df1": idx1,
#                 "endereco_df1": end1_original,
#                 "numero_df1": num1,
#                 "idx_df2": None,
#                 "endereco_df2": "",
#                 "numero_df2": None,
#                 "similaridade_texto": None,
#                 "similaridade_numero": None,
#                 "similaridade_final": None,
#                 "sugestoes_topN": ""
#             })
#             continue

#         # 4) Recalcular escores como no seu script
#         matches_final = []
#         for idx2, end2_norm, num2_int, es_score in candidatos:
#             # Similaridade de texto: vamos reescorar aproximadamente usando uma razão:
#             # Transformamos _score do ES em faixa 0-100 via min-max local.
#             # Como os candidatos já vieram ordenados por _score, usaremos um normalizador
#             # pós-loop (baseado no melhor e pior _score do lote).
#             matches_final.append({
#                 "idx2": idx2,
#                 "end2_norm": end2_norm,
#                 "num2_int": try_int(num2_int),
#                 "es_score": es_score
#             })

#         # Normaliza o _score do ES para 0..100 para combinar com "similaridade_numero"
#         es_scores = [m["es_score"] for m in matches_final]
#         max_es, min_es = max(es_scores), min(es_scores)
#         span = (max_es - min_es) if (max_es > min_es) else 1.0

#         for m in matches_final:
#             score_texto = 100.0 * (m["es_score"] - min_es) / span  # 0..100
#             # Similaridade de número (igual ao seu cálculo)
#             if num1_int is not None and m["num2_int"] is not None:
#                 diff = abs(num1_int - m["num2_int"])
#                 if diff == 0:
#                     score_numero = 100.0
#                 else:
#                     score_numero = max(0.0, 100.0 * (1.0 - diff / max(num1_int, m["num2_int"])))
#             else:
#                 score_numero = None

#             if score_numero is None:
#                 score_final = score_texto
#             else:
#                 score_final = score_texto * peso_texto + score_numero * peso_numero

#             score_final = possivel_bairro_diferente(end1_norm, m["end2_norm"], score_final)

#             m["score_texto"] = score_texto
#             m["score_numero"] = score_numero
#             m["score_final"] = score_final

#         # Ordena pelo score final
#         matches_final.sort(key=lambda x: x["score_final"], reverse=True)

#         # Melhor match
#         best = matches_final[0]
#         idx2_best = best["idx2"]

#         # Monta sugestões
#         sugestoes_formatadas = []
#         for sug in matches_final[:top_n]:
#             row2 = df2.loc[sug["idx2"]]
#             endereco_original2 = formatar_endereco(row2, colunas2)
#             numero2 = row2.get(col_num2, "") if col_num2 else ""
#             score_final_str = f"{sug['score_final']:.0f}" if sug["score_final"] is not None else "N/A"
#             sugestoes_formatadas.append(f"{endereco_original2} {numero2} | Score Final: {score_final_str}")

#         # Linha final
#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": end1_original,
#             "numero_df1": num1,
#             "idx_df2": idx2_best,
#             "endereco_df2": formatar_endereco(df2.iloc[idx2_best], colunas2),
#             "numero_df2": df2.loc[idx2_best, col_num2] if col_num2 else None,
#             "similaridade_texto": round(best["score_texto"], 2) if best["score_texto"] is not None else None,
#             "similaridade_numero": round(best["score_numero"], 2) if best["score_numero"] is not None else None,
#             "similaridade_final": round(best["score_final"], 2) if best["score_final"] is not None else None,
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#         })

#     return pd.DataFrame(resultados)

# comparador_es.py
# Versão convertida do seu comparador para usar Elasticsearch (sem RapidFuzz).
# Mantém a mesma lógica de normalização, combinação de scores e penalização por "bairro diferente".

import re
import pandas as pd
import unidecode
from num2words import num2words
from typing import Optional, Dict, Any, Iterable
from elasticsearch import Elasticsearch
from elasticsearch import helpers


# ==============================
# Utilitários de normalização (iguais/compatíveis com seu arquivo original)
# ==============================

def normalize(text):
    """
    Remove acentos, coloca tudo em minúsculas e tira espaços extras
    """
    if pd.isna(text):
        return ""
    return unidecode.unidecode(str(text)).strip().lower()

def normalizar_abreviacoes(texto):
    """
    Substitui abreviações comuns de logradouros para forma completa
    """
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

def numeros_para_texto(texto):
    """
    Substitui números inteiros no texto por palavras.
    Ex: "Rua 22 de Abril" -> "Rua vinte e dois de Abril"
    """
    def substituir(match):
        num = int(match.group())
        return num2words(num, lang='pt')
    return re.sub(r'\b\d+\b', substituir, texto)

def remover_tipo_logradouro(texto):
    """
    Remove tipos de logradouro (RUA, AVENIDA, ALAMEDA...) apenas para comparação textual.
    """
    tipos = ["acesso", "alameda", "avenida", "calcada", "chacara", "condominio",
             "corredor", "entrada", "escadao", "escadaria", "faixa", "passagem",
             "praca", "rodovia", "rua", "saida", "serra", "travessa", "travessao",
             "travessia", "viela"]
    texto = " " + texto.lower() + " "
    for t in tipos:
        texto = texto.replace(f" {t} ", " ")
    return texto.strip()

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

def possivel_bairro_diferente(end1, end2, score_final, penalizacao=0.95):
    """
    Penaliza o score final se os últimos tokens (possíveis bairros) forem diferentes.
    """
    tokens1 = end1.split()
    tokens2 = end2.split()
    if tokens1 and tokens2:
        ult1, ult2 = tokens1[-1], tokens2[-1]
        if ult1 != ult2:
            return score_final * penalizacao
    return score_final

def try_int(n) -> Optional[int]:
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
    except Exception:
        return None


import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Acessa as variáveis
ELASTICSEARCH_PW = os.getenv("ELASTICSEARCH_PW")

# ==============================
# Cliente & Índice do Elasticsearch
# ==============================

def make_es_client(
    hosts: str = "https://localhost:9200",
    username: Optional[str] = "elastic",
    password: Optional[str] = ELASTICSEARCH_PW,
    ca_certs: Optional[str] = "/etc/elasticsearch/certs/http_ca.crt",
    verify_certs: Optional[bool] = True,
    **kwargs
) -> Elasticsearch:
    """
    Cria cliente do Elasticsearch (ES 8.x).
    Exemplo:
        es = make_es_client(
            "https://localhost:9200",
            username="elastic",
            password="SENHA",
            ca_certs="/etc/elasticsearch/certs/http_ca.crt"
        )
    """
    params: Dict[str, Any] = dict(
        hosts=[hosts],
        request_timeout=60,
    )
    if username and password:
        params["basic_auth"] = (username, password)
    if ca_certs:
        params["ca_certs"] = ca_certs
    if verify_certs is not None:
        params["verify_certs"] = verify_certs
    params.update(kwargs)
    return Elasticsearch(**params)

def ensure_index(
    es: Elasticsearch,
    index_name: str,
    recreate: bool = False
):
    """
    Cria (ou recria) o índice com um analisador simples para endereços.
    """
    # Configurações e mapeamento: analisador minúsculas + remover acentos
    settings = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "endereco_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "dynamic": True,
            "properties": {
                "endereco_original": {"type": "text", "analyzer": "endereco_analyzer"},
                "endereco_normalizado": {"type": "text", "analyzer": "endereco_analyzer"},
                "numero": {"type": "integer"},
                "orig_index": {"type": "long"}
            }
        }
    }

    exists = es.indices.exists(index=index_name)
    if exists and recreate:
        es.indices.delete(index=index_name, ignore_unavailable=True)
        exists = False

    if not exists:
        es.indices.create(index=index_name, **settings)


def indexar_enderecos_elasticsearch(
    es: Elasticsearch,
    df_ref: pd.DataFrame,
    colunas_ref,
    col_num_ref: Optional[str],
    index_name: str = "enderecos_ref",
    recreate_index: bool = False,
) -> None:
    """
    Indexa o DataFrame de referência (df_ref) no Elasticsearch.
    - enderecos_normalizado: texto normalizado para busca
    - endereco_original: texto original para exibição
    - numero: inteiro (se disponível)
    - orig_index: índice original do df_ref (útil para rastreabilidade)
    """
    ensure_index(es, index_name=index_name, recreate=recreate_index)

    df_ref = df_ref.copy()
    df_ref["endereco_normalizado"] = montar_endereco(df_ref, colunas_ref, excluir_col_num=col_num_ref)

    def gen_actions() -> Iterable[Dict[str, Any]]:
        for idx, row in df_ref.iterrows():
            numero = try_int(row.get(col_num_ref)) if col_num_ref else None
            doc = {
                "endereco_original": formatar_endereco(row, colunas_ref),
                "endereco_normalizado": row["endereco_normalizado"],
                "numero": numero,
                "orig_index": int(idx) if try_int(idx) is not None else None
            }
            # Também armazenar as colunas originais para reconstruir (opcional)
            for c in colunas_ref:
                doc[str(c)] = None if pd.isna(row.get(c)) else str(row.get(c))

            yield {
                "_index": index_name,
                "_id": str(idx),  # opcional: usa o índice do DF como _id
                "_source": doc
            }

    # bulk index
    helpers.bulk(es, gen_actions(), request_timeout=120)


# ==============================
# Busca e comparação (df1 vs ES)
# ==============================

def _buscar_candidatos_textuais(
    es: Elasticsearch,
    index_name: str,
    termo: str,
    size: int = 200
):
    """
    Busca candidatos por similaridade textual usando fuzziness AUTO.
    Retorna hits completos (inclui _score e _source).
    """
    query = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "endereco_normalizado": {
                                "query": termo,
                                "fuzziness": "AUTO",
                                "operator": "and"
                            }
                        }
                    }
                ],
                "should": [
                    {
                        "match_phrase": {
                            "endereco_normalizado": {
                                "query": termo,
                                "slop": 2
                            }
                        }
                    }
                ]
            }
        }
    }
    resp = es.search(index=index_name, body=query, request_timeout=60)
    return resp.get("hits", {}).get("hits", [])


def comparar_enderecos_es(
    es: Elasticsearch,
    df1: pd.DataFrame,
    colunas1,
    index_name: str,
    col_num1: Optional[str] = None,
    limiar_similaridade: int = 85,
    peso_texto: float = 0.7,
    peso_numero: float = 0.3,
    top_n: int = 5,
    candidatos_por_query: int = 200,
) -> pd.DataFrame:
    """
    Compara endereços do df1 com a base indexada no Elasticsearch (index_name).

    Estratégia:
    1) Normaliza df1 (como no original).
    2) Para cada endereço normalizado do df1, busca candidatos no ES (match com fuzziness AUTO).
    3) Normaliza o score textual do ES relativo ao melhor da mesma consulta (0..100).
    4) Calcula similaridade numérica (mesma fórmula do seu código).
    5) Combina (peso_texto, peso_numero) e aplica penalidade de "bairro diferente".
    6) Seleciona melhor match e top-N sugestões.

    Retorna DataFrame com as mesmas colunas do seu resultado original.
    """
    df1 = df1.copy()
    df1["endereco_normalizado"] = montar_endereco(df1, colunas1, excluir_col_num=col_num1)
    resultados = []

    for idx1, endereco1_norm in df1["endereco_normalizado"].items():
        # Busca candidatos no ES
        hits = _buscar_candidatos_textuais(
            es, index_name=index_name, termo=endereco1_norm, size=candidatos_por_query
        )

        if not hits:
            # Sem candidatos
            resultados.append({
                "idx_df1": idx1,
                "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
                "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
                "idx_df2": None,
                "endereco_df2": None,
                "numero_df2": None,
                "similaridade_texto": 0.0,
                "similaridade_numero": None,
                "similaridade_final": 0.0,
                "sugestoes_topN": ""
            })
            continue

        # Normaliza o score textual do ES por consulta (top hit vira 100)
        max_score = max(h["_score"] or 0.0 for h in hits) or 1.0

        num1 = df1.loc[idx1, col_num1] if col_num1 else None
        num1_int = try_int(num1)

        candidatos = []
        for h in hits:
            src = h.get("_source", {})
            end2_norm = src.get("endereco_normalizado", "")
            end2_orig = src.get("endereco_original", "")
            num2_int = src.get("numero", None)

            # similaridade de texto normalizada (0..100)
            score_texto = (h["_score"] / max_score) * 100.0

            # similaridade de número
            if (num1_int is not None) and (num2_int is not None):
                diff = abs(int(num1_int) - int(num2_int))
                if diff == 0:
                    score_numero = 100.0
                else:
                    score_numero = max(0.0, 100.0 * (1.0 - diff / max(int(num1_int), int(num2_int))))
            else:
                score_numero = None

            # combinação
            if score_numero is None:
                score_final = score_texto
            else:
                score_final = score_texto * peso_texto + score_numero * peso_numero

            # penalização por "bairro" diferente (último token)
            score_final = possivel_bairro_diferente(endereco1_norm, end2_norm, score_final)

            candidatos.append({
                "id": h.get("_id"),
                "orig_index": src.get("orig_index"),
                "endereco_original": end2_orig,
                "endereco_normalizado": end2_norm,
                "numero": num2_int,
                "score_texto": score_texto,
                "score_numero": score_numero,
                "score_final": score_final
            })

        # ordena por score_final desc
        candidatos.sort(key=lambda x: x["score_final"], reverse=True)

        melhor = candidatos[0]
        sugestoes = []
        for c in candidatos[:top_n]:
            numero_str = "" if c["numero"] is None else f" {c['numero']}"
            sugestoes.append(f"{c['endereco_original']}{numero_str} | Score Final: {c['score_final']:.0f}")

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
            "numero_df1": num1,
            # salvamos tanto _id do ES quanto o índice original da linha do df2
            "idx_df2": melhor["orig_index"] if melhor["orig_index"] is not None else melhor["id"],
            "endereco_df2": melhor["endereco_original"],
            "numero_df2": melhor["numero"],
            "similaridade_texto": round(melhor["score_texto"], 2),
            "similaridade_numero": round(melhor["score_numero"], 2) if melhor["score_numero"] is not None else None,
            "similaridade_final": round(melhor["score_final"], 2),
            "sugestoes_topN": "; ".join(sugestoes)
        })

    # Opcional: filtrar por limiar de similaridade final
    if limiar_similaridade is not None:
        df_res = pd.DataFrame(resultados)
        return df_res[df_res["similaridade_final"] >= limiar_similaridade].reset_index(drop=True)

    return pd.DataFrame(resultados)


# ==============================
# Exemplo de uso (comentado)
# ==============================
"""
if __name__ == "__main__":
    # 1) Conectar ao ES
    es = make_es_client(
        hosts="https://localhost:9200",
        username="elastic",
        password="SUA_SENHA",
        ca_certs="/etc/elasticsearch/certs/http_ca.crt",
    )

    # 2) Ler seus CSVs e definir colunas
    df1 = pd.read_csv("entrada.csv")      # base a procurar
    df2 = pd.read_csv("referencia.csv")   # base de referência

    colunas1 = ["logradouro", "bairro", "cidade", "estado"]  # Exemplo
    colunas2 = ["logradouro", "bairro", "cidade", "estado"]  # Exemplo
    col_num1 = "numero"
    col_num2 = "numero"

    # 3) Indexar df2 (recriar índice opcionalmente)
    indexar_enderecos_elasticsearch(
        es, df_ref=df2, colunas_ref=colunas2, col_num_ref=col_num2,
        index_name="enderecos_ref", recreate_index=True
    )

    # 4) Comparar df1 contra ES
    df_result = comparar_enderecos_elasticsearch(
        es, df1=df1, colunas1=colunas1,
        index_name="enderecos_ref", col_num1=col_num1,
        limiar_similaridade=85, peso_texto=0.7, peso_numero=0.3, top_n=5
    )

    print(df_result.head())
"""

# ESTE CODIGO ESTÁ DANDO ERRO, VER O PRIMEIRO CODIGO MESMO