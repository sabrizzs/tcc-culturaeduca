from elasticsearch import Elasticsearch, helpers
import pandas as pd
import unidecode
import time

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


def montar_endereco(df, colunas, excluir_col_num=None):
    def concat_normaliza(row):
        partes = []
        for col in colunas:
            if col == excluir_col_num:
                continue
            val = row.get(col, "")
            if pd.isna(val) or str(val).strip() == "":
                val = ""
            partes.append(str(val))
        texto = " ".join(partes)
        texto = normalize(texto)
        texto = normalizar_abreviacoes(texto)
        texto = remover_tipo_logradouro(texto)
        return texto
    return df.apply(concat_normaliza, axis=1)


def formatar_endereco(row, colunas):
    return " ".join([str(row.get(col, "") or "") for col in colunas]).strip()


def try_int(n):
    if pd.isna(n): return None
    try: return int(float(str(n).strip()))
    except: return None


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

    # es = Elasticsearch("http://localhost:9200")

    # Verifica se o Elasticsearch está acessível
    if not es.ping():
        raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
    
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, mappings={
        "properties": {
            "endereco_normalizado": {"type": "text"},
            "original_index": {"type": "integer"}
        }
    })

    actions = [
        {
            "_index": index_name,
            "_id": i,
            "_source": {
                "endereco_normalizado": row["endereco_normalizado"],
                "original_index": i
            }
        }
        for i, row in df.iterrows()
    ]

    helpers.bulk(es, actions)
    return es


def buscar_similares_elasticsearch(es, endereco, index_name, size=100):
    query = {
        "query": {
            "match": {
                "endereco_normalizado": {
                    "query": endereco,
                    "fuzziness": "AUTO"
                }
            }
        }
    }
    res = es.search(index=index_name, body=query, size=size)
    return [(hit["_source"]["original_index"], hit["_score"]) for hit in res["hits"]["hits"]]


def comparar_enderecos_es(df1, df2, colunas1, colunas2,
                          col_num1=None, col_num2=None,
                          peso_texto=0.7, peso_numero=0.3,
                          top_n=5, index_name="enderecos_ref"):
    
    df1 = df1.copy()
    df2 = df2.copy()

    df1["endereco_normalizado"] = montar_endereco(df1, colunas1, excluir_col_num=col_num1)
    df2["endereco_normalizado"] = montar_endereco(df2, colunas2, excluir_col_num=col_num2)

    es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
    time.sleep(1)  # Espera para o índice estar pronto

    resultados = []

    for idx1, endereco1 in df1["endereco_normalizado"].items():
        num1 = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        similares = buscar_similares_elasticsearch(es, endereco1, index_name)

        matches_final = []
        for idx2, score_texto_raw in similares:
            num2 = try_int(df2.loc[idx2, col_num2]) if col_num2 else None

            if num1 is not None and num2 is not None:
                diff = abs(num1 - num2)
                score_numero = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1, num2)))
            else:
                score_numero = None

            if score_numero is None:
                score_final = score_texto_raw
            else:
                score_final = score_texto_raw * peso_texto + score_numero * peso_numero

            matches_final.append((idx2, score_texto_raw, score_numero, score_final))

        matches_final.sort(key=lambda x: x[3], reverse=True)
        idx2, score_texto, score_numero, melhor_score = matches_final[0] if matches_final else (None, 0, None, 0)

        sugestoes = []
        for idx2_sug, st, sn, sf in matches_final[:top_n]:
            sugestoes.append(
                f"{formatar_endereco(df2.loc[idx2_sug], colunas2)} {df2.loc[idx2_sug, col_num2] if col_num2 else ''} | Score Final: {sf:.0f}"
            )

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
            "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(df2.loc[idx2], colunas2) if idx2 is not None else None,
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 and idx2 is not None else None,
            "similaridade_texto": round(score_texto, 2),
            "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
            "similaridade_final": round(melhor_score, 2),
            "sugestoes_topN": "; ".join(sugestoes)
        })

    return pd.DataFrame(resultados)
