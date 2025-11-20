# indexacao_elasticsearch.py

import pandas as pd
import time
from elasticsearch import Elasticsearch, helpers

"""
Run comparador - script principal
Responsabilidades:
1. Carregar arquivo normalizado do cnefe.
2. Indexar os dados do arquivo cnefe.
"""

# -------------------
# Configurações do usuário - Dados de Entrada
# -------------------

arquivo_cnefe_normalizado = "/home/samantha/tcc-culturaeduca/source/nov25/api/datasets_normalizados/normalizado_roraima_cnefe.csv" # dados dos arquivos do cnefe
ELASTICSEARCH_PW = "HO2Vv2MWa=jTr-EHSmEt" # chave do elasticsearch

# -------------------
# Funções de indexação
# -------------------
from elasticsearch.helpers import BulkIndexError

def indexar_enderecos_elasticsearch(
    df,
    index_name="enderecos_ref",
    recreate=True,
    col_logradouro="logradouro_normalizado",
    col_bairro="bairro_normalizado",
    col_num="numero_int",
):
    try:
        es = Elasticsearch(
            "https://localhost:9200",
            basic_auth=("elastic", ELASTICSEARCH_PW),
            ca_certs="/etc/elasticsearch/certs/http_ca.crt",
        )

        if not es.ping():
            raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
        
        if recreate:
            if es.indices.exists(index=index_name):
                es.indices.delete(index=index_name)

            es.indices.create(index=index_name, mappings={
                "properties": {
                    "logradouro_normalizado": {"type": "text"},
                    "bairro_normalizado": {"type": "text"},
                    "numero": {"type": "integer"},
                    "original_index": {"type": "integer"},
                }
            })

        def safe_str(x):
            # transforma NaN/None em None (null no JSON); senão, string
            if pd.isna(x):
                return None
            return str(x)

        actions = []
        for i, row in df.iterrows():
            # logradouro e bairro sem NaN
            logradouro = safe_str(row[col_logradouro])
            bairro = safe_str(row[col_bairro])

            # número: tenta converter, se não der põe None
            numero_val = row[col_num]
            try:
                numero_int = int(numero_val) if pd.notna(numero_val) else None
            except Exception:
                numero_int = None

            actions.append({
                "_index": index_name,
                "_id": i,
                "_source": {
                    "logradouro_normalizado": logradouro,
                    "bairro_normalizado": bairro,
                    "numero": numero_int,
                    "original_index": i,
                }
            })

        helpers.bulk(es, actions)
        return True

    except BulkIndexError as e:
        print(f"{len(e.errors)} documentos falharam ao indexar.")
        for err in e.errors[:5]:
            print(err)
        return False
    except Exception as e:
        print("Erro geral:", str(e))
        return False

# def indexar_enderecos_elasticsearch(df, index_name="enderecos_ref", recreate=True, col_logradouro="logradouro_normalizado", col_bairro="bairro_normalizado", col_num="numero_int"):
#     try:
#         es = Elasticsearch(
#             "https://localhost:9200",
#             basic_auth=("elastic", ELASTICSEARCH_PW),
#             ca_certs="/etc/elasticsearch/certs/http_ca.crt",
#         )

#         # Verifica se o Elasticsearch está acessível
#         if not es.ping():
#             raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
        
#         if recreate:
#             # se existir indice ele deleta para recriar
#             if es.indices.exists(index=index_name):
#                 es.indices.delete(index=index_name)

#             es.indices.create(index=index_name, mappings={
#                 "properties": {
#                     "logradouro_normalizado": {"type": "text"},
#                     "bairro_normalizado": {"type": "text"},
#                     "numero": {"type": "integer"},
#                     "original_index": {"type": "integer"}
#                 }
#             })

#         actions = [
#             {
#                 "_index": index_name,
#                 "_id": i,
#                 "_source": {
#                     "logradouro_normalizado": row[col_logradouro],
#                     "bairro_normalizado": row[col_bairro],
#                     "numero": int(row[col_num]),
#                     "original_index": i
#                 }
#             }
#             for i, row in df.iterrows()
#         ]

#         helpers.bulk(es, actions)
#     except Exception as e:
#         print(str(e))

def indexar_elasticsearch(df2):
    """
    Compara endereços usando Elasticsearch.
    Recebe DataFrames já normalizados.
    Retorna DataFrame padronizado com melhores matches.
    Faz deduplicação ANTES de inserir no resultado, evitando repetir linhas
    com os mesmos:
      endereco_df1, endereco_df2, numero_df1, numero_df2,
      bairro_df1, bairro_df2,
      latitude_verdadeira, longitude_verdadeira, cd_setor_verdadeiro,
      latitude_resultante, longitude_resultante, cd_setor_resultante.
    """

    index_name = "enderecos_ref"

    success = indexar_enderecos_elasticsearch(df2, index_name=index_name)
    if success:
        time.sleep(1)  # Espera para o índice estar pronto
        print('✅ Indexação realizada com sucesso!')


# -------------------
# Execução
# -------------------

start_time = time.time()

df2 = pd.read_csv(arquivo_cnefe_normalizado, sep=";", dtype=str)
indexar_elasticsearch(df2)
elapsed = time.time() - start_time
print(f"Tempo de execução: {elapsed:.2f} segundos.")

 


