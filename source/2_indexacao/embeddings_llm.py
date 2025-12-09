# #!/usr/bin/env python
# import os
# import math
# import pandas as pd
# import psycopg2
# from psycopg2.extras import execute_values
# from sentence_transformers import SentenceTransformer

# # ========================
# # CONFIGURAÇÕES
# # ========================

# ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_diadema_cnefe.csv" # arquivo de entrada
# COLS_ENDERECO = ["logradouro_normalizado", "numero_int", "bairro_normalizado"]
# COD_UNICO = "CO_UNIDADE"

# PG_DSN = os.getenv(
#     "PG_DSN",
#     "dbname=tcc user=postgres password=password host=localhost port=5432",
# )

# TABELA_EMBEDDINGS = "cnefe_diadema_embeddings"
# BATCH_SIZE = 512  # quantos textos por batch de embedding
# CHUNK_ROWS = 10_000  # quantas linhas do CSV ler por vez (para não estourar memória)

# # MODELO = "sentence-transformers/all-MiniLM-L6-v2"  # dim=384
# MODELO = "paraphrase-MiniLM-L3-v2" # dim=256


# # ========================
# # FUNÇÕES AUXILIARES
# # ========================

# def conectar_pg():
#     conn = psycopg2.connect(PG_DSN)
#     conn.autocommit = False
#     return conn


# def montar_texto_endereco(row):
#     """
#     Monta o texto do endereço a partir das colunas normalizadas.
#     Ajuste conforme seu pipeline de normalização.
#     """
#     partes = []
#     for col in COLS_ENDERECO:
#         valor = str(row.get(col, "") or "").strip()
#         if valor:
#             partes.append(valor)
#     return " ".join(partes)


# def vetor_para_pgvector(vec):
#     """
#     Converte um np.array/list de floats para string no formato pgvector: [0.1,0.2,...]
#     """
#     return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"


# # ========================
# # MAIN
# # ========================

# def main():
#     print("Carregando modelo de embeddings...")
#     model = SentenceTransformer(MODELO)
#     print("Modelo carregado.")

#     conn = conectar_pg()
#     cur = conn.cursor()

#     # Garante que a tabela existe (opcional se você já criou via SQL)
#     cur.execute(f"""
#         CREATE TABLE IF NOT EXISTS {TABELA_EMBEDDINGS} (
#             id_bigserial      BIGSERIAL PRIMARY KEY,
#             cod_unico         text,
#             texto_endereco    text,
#             embedding         vector({model.get_sentence_embedding_dimension()})
#         );
#     """)
#     conn.commit()

#     print("Lendo CSV em chunks...")
#     reader = pd.read_csv(ARQUIVO_ENTRADA, sep=";", dtype=str, chunksize=CHUNK_ROWS)

#     total_processado = 0
#     for chunk_idx, df_chunk in enumerate(reader):
#         print(f">>> Chunk {chunk_idx}, linhas: {len(df_chunk)}")

#         # Monte o texto do endereço
#         textos = df_chunk.apply(montar_texto_endereco, axis=1).tolist()

#         # Cod_unico: escolha uma coluna que identifique o endereço
#         # Exemplo: "cod_unico_endereco" ou combinação de colunas
#         if COD_UNICO in df_chunk.columns:
#             cods = df_chunk[COD_UNICO].astype(str).tolist()
#         else:
#             cods = df_chunk.index.astype(str).tolist()

#         # Gera embeddings em batches
#         registros_para_inserir = []

#         n = len(textos)
#         num_batches = math.ceil(n / BATCH_SIZE)
#         for b in range(num_batches):
#             ini = b * BATCH_SIZE
#             fim = min((b + 1) * BATCH_SIZE, n)
#             batch_textos = textos[ini:fim]
#             batch_cods = cods[ini:fim]

#             embeddings = model.encode(batch_textos, show_progress_bar=False, convert_to_numpy=True)

#             for cod, texto, emb in zip(batch_cods, batch_textos, embeddings):
#                 registros_para_inserir.append(
#                     (cod, texto, vetor_para_pgvector(emb))
#                 )

#         # Insere no Postgres em lote
#         if registros_para_inserir:
#             sql = f"""
#                 INSERT INTO {TABELA_EMBEDDINGS} (cod_unico, texto_endereco, embedding)
#                 VALUES %s
#             """
#             execute_values(cur, sql, registros_para_inserir)
#             conn.commit()

#         total_processado += len(df_chunk)
#         print(f"Total processado até agora: {total_processado}")

#     cur.close()
#     conn.close()
#     print("Concluído! Total de linhas processadas:", total_processado)


# if __name__ == "__main__":
#     main()

# ============================
# COM PCA - vetor com 128 dim
# ============================

# #!/usr/bin/env python
# import os
# import numpy as np
# import pandas as pd
# import psycopg2
# from psycopg2.extras import execute_values
# from sentence_transformers import SentenceTransformer
# from sklearn.decomposition import PCA

# # ========================
# # CONFIGURAÇÕES
# # ========================

# ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_diadema_cnefe.csv"

# COL_LOGRADOURO = "logradouro_normalizado"
# COL_NUMERO = "numero_int"
# COL_BAIRRO = "bairro_normalizado"

# COD_UNICO = "CO_UNIDADE"

# PG_DSN = os.getenv(
#     "PG_DSN",
#     "dbname=tcc user=postgres password=password host=localhost port=5432",
# )

# TABELA_EMBEDDINGS = "cnefe_diadema_embeddings"
# CHUNK_ROWS = 10_000  # linhas por chunk

# MODELO_BASE = "paraphrase-MiniLM-L3-v2"
# DIM_FINAL = 128  # dimensão alvo dos embeddings de cada campo


# # ========================
# # FUNÇÕES AUXILIARES
# # ========================

# def conectar_pg():
#     conn = psycopg2.connect(PG_DSN)
#     conn.autocommit = False
#     return conn


# def vetor_para_pgvector(vec):
#     """
#     Converte um vetor 1D (list/np.ndarray) para o formato pgvector: [0.123456,0.234567,...]
#     """
#     arr = np.asarray(vec, dtype=float).ravel()
#     valores = (f"{x:.6f}" for x in arr)
#     return "[" + ",".join(valores) + "]"


# # ========================
# # MAIN
# # ========================

# def main():
#     print("Carregando modelo base...")
#     base_model = SentenceTransformer(MODELO_BASE)
#     print(f"Modelo carregado: {MODELO_BASE}")
#     print(f"Dimensão original: {base_model.get_sentence_embedding_dimension()}")

#     pca = None  # será definido no primeiro chunk

#     conn = conectar_pg()
#     cur = conn.cursor()

#     print(f"→ Cada embedding (logradouro/numero/bairro) terá dimensão até {DIM_FINAL} usando PCA.")

#     # Criar tabela de embeddings (3 vetores separados)
#     cur.execute(f"""
#         CREATE TABLE IF NOT EXISTS {TABELA_EMBEDDINGS} (
#             id BIGSERIAL PRIMARY KEY,
#             cod_unico              text,
#             logradouro             text,
#             numero                 text,
#             bairro                 text,
#             logradouro_embedding   vector({DIM_FINAL}),
#             numero_embedding       vector({DIM_FINAL}),
#             bairro_embedding       vector({DIM_FINAL})
#         );
#     """)
#     conn.commit()

#     print("Lendo CSV em chunks...")
#     reader = pd.read_csv(ARQUIVO_ENTRADA, sep=";", dtype=str, chunksize=CHUNK_ROWS)

#     total_processado = 0
#     for chunk_idx, df_chunk in enumerate(reader):
#         print(f">>> Chunk {chunk_idx}, linhas: {len(df_chunk)}")

#         # Extrai textos individuais
#         logradouros = df_chunk[COL_LOGRADOURO].fillna("").astype(str).tolist()
#         numeros = df_chunk[COL_NUMERO].fillna("").astype(str).tolist()
#         bairros = df_chunk[COL_BAIRRO].fillna("").astype(str).tolist()

#         if COD_UNICO in df_chunk.columns:
#             cods = df_chunk[COD_UNICO].astype(str).tolist()
#         else:
#             cods = df_chunk.index.astype(str).tolist()

#         # Gera embeddings "cheios" (384 dims) para cada componente
#         show_bar = (chunk_idx == 0)
#         emb_log_full = base_model.encode(
#             logradouros, show_progress_bar=show_bar, convert_to_numpy=True
#         )
#         emb_num_full = base_model.encode(
#             numeros, show_progress_bar=False, convert_to_numpy=True
#         )
#         emb_bairro_full = base_model.encode(
#             bairros, show_progress_bar=False, convert_to_numpy=True
#         )

#         # Treinar PCA no primeiro chunk usando todos os tipos combinados
#         if chunk_idx == 0:
#             # empilha todos embeddings (3 * n amostras)
#             embeddings_concat = np.vstack([emb_log_full, emb_num_full, emb_bairro_full])
#             n_samples_total, n_features = embeddings_concat.shape
#             max_components = min(DIM_FINAL, n_samples_total, n_features)

#             if max_components < DIM_FINAL:
#                 print(
#                     f"AVISO: poucas amostras ({n_samples_total}) para PCA={DIM_FINAL}. "
#                     f"Usando n_components={max_components} e preenchendo o resto com zeros."
#                 )

#             pca = PCA(n_components=max_components)
#             print("Treinando PCA com o primeiro chunk (logradouro+numero+bairro)...")
#             pca.fit(embeddings_concat)
#             print("PCA treinado.")

#         # Aplica PCA em cada tipo de embedding
#         emb_log_red = pca.transform(emb_log_full)
#         emb_num_red = pca.transform(emb_num_full)
#         emb_bairro_red = pca.transform(emb_bairro_full)

#         # Se max_components < DIM_FINAL, preenche com zeros para ter sempre DIM_FINAL
#         if emb_log_red.shape[1] < DIM_FINAL:
#             pad_width = DIM_FINAL - emb_log_red.shape[1]
#             emb_log_red = np.pad(
#                 emb_log_red,
#                 pad_width=((0, 0), (0, pad_width)),
#                 mode="constant",
#                 constant_values=0.0,
#             )
#             emb_num_red = np.pad(
#                 emb_num_red,
#                 pad_width=((0, 0), (0, pad_width)),
#                 mode="constant",
#                 constant_values=0.0,
#             )
#             emb_bairro_red = np.pad(
#                 emb_bairro_red,
#                 pad_width=((0, 0), (0, pad_width)),
#                 mode="constant",
#                 constant_values=0.0,
#             )

#         registros_para_inserir = []
#         for cod, log, num, bai, e_log, e_num, e_bai in zip(
#             cods, logradouros, numeros, bairros,
#             emb_log_red, emb_num_red, emb_bairro_red
#         ):
#             registros_para_inserir.append(
#                 (
#                     cod,
#                     log,
#                     num,
#                     bai,
#                     vetor_para_pgvector(e_log),
#                     vetor_para_pgvector(e_num),
#                     vetor_para_pgvector(e_bai),
#                 )
#             )

#         if registros_para_inserir:
#             sql = f"""
#                 INSERT INTO {TABELA_EMBEDDINGS} (
#                     cod_unico,
#                     logradouro,
#                     numero,
#                     bairro,
#                     logradouro_embedding,
#                     numero_embedding,
#                     bairro_embedding
#                 )
#                 VALUES %s
#             """
#             execute_values(cur, sql, registros_para_inserir)
#             conn.commit()

#         total_processado += len(df_chunk)
#         print(f"Total processado até agora: {total_processado}")

#     cur.close()
#     conn.close()
#     print("Concluído! Total de linhas processadas:", total_processado)


# if __name__ == "__main__":
#     main()


# ========================
# SEM PCA - utiliza paraphrase-MiniLM-L3-v2
# ========================


#!/usr/bin/env python
import os
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# ========================
# CONFIGURAÇÕES
# ========================

ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_diadema_entrada.csv"

COL_LOGRADOURO = "logradouro_normalizado"
COL_NUMERO = "numero_int"
COL_BAIRRO = "bairro_normalizado"

COD_UNICO = "CO_UNIDADE" # ATENÇAO COM O NOME DESTA COLUNA

PG_DSN = os.getenv(
    "PG_DSN",
    "dbname=tcc user=postgres password=password host=localhost port=5432",
)

TABELA_EMBEDDINGS = "entrada_diadema_embeddings"
CHUNK_ROWS = 10_000  # linhas por chunk

MODELO_BASE = "paraphrase-MiniLM-L3-v2"


# ========================
# FUNÇÕES AUXILIARES
# ========================

def conectar_pg():
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    return conn


def vetor_para_pgvector(vec):
    """
    Converte um vetor 1D (list/np.ndarray) para o formato pgvector: [0.123456,0.234567,...]
    """
    arr = np.asarray(vec, dtype=float).ravel()
    valores = (f"{x:.6f}" for x in arr)
    return "[" + ",".join(valores) + "]"


# ========================
# MAIN
# ========================

def main():
    print("Carregando modelo base...")
    base_model = SentenceTransformer(MODELO_BASE)
    print(f"Modelo carregado: {MODELO_BASE}")
    dim_embedding = base_model.get_sentence_embedding_dimension()
    print(f"Dimensão original do embedding: {dim_embedding}")

    conn = conectar_pg()
    cur = conn.cursor()

    print(f"→ Cada embedding (logradouro/numero/bairro) terá dimensão {dim_embedding} (sem PCA).")

    # Criar tabela de embeddings (3 vetores separados)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_EMBEDDINGS} (
            id BIGSERIAL PRIMARY KEY,
            cod_unico              text,
            logradouro             text,
            numero                 text,
            bairro                 text,
            logradouro_embedding   vector({dim_embedding}),
            numero_embedding       vector({dim_embedding}),
            bairro_embedding       vector({dim_embedding})
        );
    """)
    conn.commit()

    print("Lendo CSV em chunks...")
    reader = pd.read_csv(ARQUIVO_ENTRADA, sep=";", dtype=str, chunksize=CHUNK_ROWS)

    total_processado = 0
    for chunk_idx, df_chunk in enumerate(reader):
        print(f">>> Chunk {chunk_idx}, linhas: {len(df_chunk)}")

        # Extrai textos individuais
        logradouros = df_chunk[COL_LOGRADOURO].fillna("").astype(str).tolist()
        numeros = df_chunk[COL_NUMERO].fillna("").astype(str).tolist()
        bairros = df_chunk[COL_BAIRRO].fillna("").astype(str).tolist()

        if COD_UNICO in df_chunk.columns:
            cods = df_chunk[COD_UNICO].astype(str).tolist()
        else:
            cods = df_chunk.index.astype(str).tolist()

        show_bar = (chunk_idx == 0)

        # Gera embeddings na dimensão original do modelo (sem PCA)
        emb_log = base_model.encode(
            logradouros, show_progress_bar=show_bar, convert_to_numpy=True
        )
        emb_num = base_model.encode(
            numeros, show_progress_bar=False, convert_to_numpy=True
        )
        emb_bairro = base_model.encode(
            bairros, show_progress_bar=False, convert_to_numpy=True
        )

        registros_para_inserir = []
        for cod, log, num, bai, e_log, e_num, e_bai in zip(
            cods, logradouros, numeros, bairros,
            emb_log, emb_num, emb_bairro
        ):
            registros_para_inserir.append(
                (
                    cod,
                    log,
                    num,
                    bai,
                    vetor_para_pgvector(e_log),
                    vetor_para_pgvector(e_num),
                    vetor_para_pgvector(e_bai),
                )
            )

        if registros_para_inserir:
            sql = f"""
                INSERT INTO {TABELA_EMBEDDINGS} (
                    cod_unico,
                    logradouro,
                    numero,
                    bairro,
                    logradouro_embedding,
                    numero_embedding,
                    bairro_embedding
                )
                VALUES %s
            """
            execute_values(cur, sql, registros_para_inserir)
            conn.commit()

        total_processado += len(df_chunk)
        print(f"Total processado até agora: {total_processado}")

    cur.close()
    conn.close()
    print("Concluído! Total de linhas processadas:", total_processado)


if __name__ == "__main__":
    main()
