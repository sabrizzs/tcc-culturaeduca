import os
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# --------------------
# Configurações
# --------------------

ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_rondonia_cnefe.csv"

COL_LOGRADOURO = "logradouro_normalizado"
COL_NUMERO = "numero_int"
COL_BAIRRO = "bairro_normalizado"

COD_UNICO = "COD_UNICO_ENDERECO" # ATENÇAO COM O NOME DESTA COLUNA

COLS_NECESSARIAS = [COD_UNICO, COL_LOGRADOURO, COL_NUMERO, COL_BAIRRO]

PG_DSN = os.getenv(
    "PG_DSN",
    "dbname=<nome_db> user=<usuario> password=<senha_db> host=localhost port=5432",
)

TABELA_EMBEDDINGS = "cnefe_rondonia_embeddings"
CHUNK_ROWS = 10_000  # linhas por chunk

MODELO_BASE = "paraphrase-MiniLM-L3-v2"


# --------------------
# Funções auxiliares
# --------------------

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


# --------------------
# main
# --------------------

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
    
    reader = pd.read_csv(
        ARQUIVO_ENTRADA,
        sep=";",
        dtype=str,
        chunksize=CHUNK_ROWS,
        usecols=[c for c in COLS_NECESSARIAS if c is not None],
    )


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
