# ============================
# COM PCA - vetor com 128 dim
# ============================

#!/usr/bin/env python
import os
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA

# ========================
# CONFIGURAÇÕES
# ========================


# ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_sao_paulo_cnefe.csv"
ARQUIVO_ENTRADA = "/home/samantha/tcc-culturaeduca/source/1_normalizacao/datasets_normalizados/normalizado_mun_sp_cnefe.csv"

COL_LOGRADOURO = "logradouro_normalizado"
COL_NUMERO = "numero_int"
COL_BAIRRO = "bairro_normalizado"

COD_UNICO = "COD_UNICO_ENDERECO" # ATENÇAO COM O NOME DESTA COLUNA
# COD_UNICO = "_id" # ATENÇAO COM O NOME DESTA COLUNA

COLS_NECESSARIAS = [COD_UNICO, COL_LOGRADOURO, COL_NUMERO, COL_BAIRRO]

PG_DSN = os.getenv(
    "PG_DSN",
    "dbname=tcc user=postgres password=password host=localhost port=5432",
)

TABELA_EMBEDDINGS = "cnefe_mun_sp_embeddings"
CHUNK_ROWS = 10_000  # linhas por chunk

MODELO_BASE = "paraphrase-MiniLM-L3-v2"
DIM_FINAL = 128  # dimensão alvo dos embeddings de cada campo


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
    print(f"Dimensão original: {base_model.get_sentence_embedding_dimension()}")

    pca = None  # será definido no primeiro chunk

    conn = conectar_pg()
    cur = conn.cursor()

    print(f"→ Cada embedding (logradouro/numero/bairro) terá dimensão até {DIM_FINAL} usando PCA.")

    # Criar tabela de embeddings (3 vetores separados)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_EMBEDDINGS} (
            id BIGSERIAL PRIMARY KEY,
            cod_unico              text,
            logradouro             text,
            numero                 text,
            bairro                 text,
            logradouro_embedding   vector({DIM_FINAL}),
            numero_embedding       vector({DIM_FINAL}),
            bairro_embedding       vector({DIM_FINAL})
        );
    """)
    conn.commit()

    print("Lendo CSV em chunks...")
    # reader = pd.read_csv(ARQUIVO_ENTRADA, sep=";", dtype=str, chunksize=CHUNK_ROWS)
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

        # Gera embeddings "cheios" (384 dims) para cada componente
        show_bar = (chunk_idx == 0)
        emb_log_full = base_model.encode(
            logradouros, show_progress_bar=show_bar, convert_to_numpy=True
        )
        emb_num_full = base_model.encode(
            numeros, show_progress_bar=False, convert_to_numpy=True
        )
        emb_bairro_full = base_model.encode(
            bairros, show_progress_bar=False, convert_to_numpy=True
        )

        # Treinar PCA no primeiro chunk usando todos os tipos combinados
        if chunk_idx == 0:
            # empilha todos embeddings (3 * n amostras)
            embeddings_concat = np.vstack([emb_log_full, emb_num_full, emb_bairro_full])
            n_samples_total, n_features = embeddings_concat.shape
            max_components = min(DIM_FINAL, n_samples_total, n_features)

            if max_components < DIM_FINAL:
                print(
                    f"AVISO: poucas amostras ({n_samples_total}) para PCA={DIM_FINAL}. "
                    f"Usando n_components={max_components} e preenchendo o resto com zeros."
                )

            pca = PCA(n_components=max_components)
            print("Treinando PCA com o primeiro chunk (logradouro+numero+bairro)...")
            pca.fit(embeddings_concat)
            print("PCA treinado.")

        # Aplica PCA em cada tipo de embedding
        emb_log_red = pca.transform(emb_log_full)
        emb_num_red = pca.transform(emb_num_full)
        emb_bairro_red = pca.transform(emb_bairro_full)

        # Se max_components < DIM_FINAL, preenche com zeros para ter sempre DIM_FINAL
        if emb_log_red.shape[1] < DIM_FINAL:
            pad_width = DIM_FINAL - emb_log_red.shape[1]
            emb_log_red = np.pad(
                emb_log_red,
                pad_width=((0, 0), (0, pad_width)),
                mode="constant",
                constant_values=0.0,
            )
            emb_num_red = np.pad(
                emb_num_red,
                pad_width=((0, 0), (0, pad_width)),
                mode="constant",
                constant_values=0.0,
            )
            emb_bairro_red = np.pad(
                emb_bairro_red,
                pad_width=((0, 0), (0, pad_width)),
                mode="constant",
                constant_values=0.0,
            )

        registros_para_inserir = []
        for cod, log, num, bai, e_log, e_num, e_bai in zip(
            cods, logradouros, numeros, bairros,
            emb_log_red, emb_num_red, emb_bairro_red
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

