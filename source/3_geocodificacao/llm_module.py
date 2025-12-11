#!/usr/bin/env python
import os
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values 
import torch
import hnswlib
from sentence_transformers import SentenceTransformer, util

from comparador import formatar_endereco

# -------------------
# Postgres / util
# -------------------

def get_pg_connection():
    """
    Abre conexão com o Postgres usando a variável de ambiente PG_DSN.

    Exemplo de PG_DSN:
        export PG_DSN="dbname=culturaeduca user=usuario password=senha host=localhost port=5432"
    """
    dsn = os.getenv(
        "PG_DSN",
        "dbname=tcc user=postgres password=password host=localhost port=5432",
    )
    return psycopg2.connect(dsn)


def distancia_para_similaridade(distancia: float) -> float:
    """
    Converte uma distância (quanto menor melhor) em uma 'similaridade' em [0, 100].

    sim = 1 / (1 + d) * 100
    """
    if distancia is None:
        return 0.0
    return 100.0 * (1.0 / (1.0 + float(distancia)))


# -------------------
# LLM principal
# -------------------

def executar_llm(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    col_logradouro1_norm: str,
    col_logradouro2_norm: str,
    colunas_logradouro1_original: List[str],
    colunas_logradouro2_original: List[str],
    colunas_complemento1: Optional[List[str]] = None,
    colunas_complemento2: Optional[List[str]] = None,
    col_num1: Optional[str] = None,
    col_num2: Optional[str] = None,
    col_bairro1_norm: Optional[str] = None,
    col_bairro2_norm: Optional[str] = None,
    col_bairro1_original: Optional[str] = None,
    col_bairro2_original: Optional[str] = None,
    latitude_verdadeira: Optional[str] = None,
    longitude_verdadeira: Optional[str] = None,
    cd_setor_verdadeiro: Optional[str] = None,
    latitude_resultante: Optional[str] = None,
    longitude_resultante: Optional[str] = None,
    cd_setor_resultante: Optional[str] = None,
    cod_unico_endereco: Optional[str] = None,
    cod_unico_endereco_entrada: Optional[str] = None,
    top_n: int = 5,
    # Pesos para logradouro, número e bairro na distância final
    peso_logradouro: float = 0.7,
    peso_numero: float = 0.2,
    peso_bairro: float = 0.1,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Versão do algoritmo "llm" usando embeddings pré-calculados no Postgres.

    Tabelas usadas:
        - entrada_diadema_embeddings (e):
            cod_unico, logradouro_embedding, numero_embedding, bairro_embedding
        - cnefe_diadema_embeddings (c):
            cod_unico, logradouro_embedding, numero_embedding, bairro_embedding

    Para cada linha de df1 (idx_df1, com cod_unico_endereco_entrada), busca:

        SELECT
            c.cod_unico,
            dist_log,
            dist_num,
            dist_bairro,
            distancia_final (ponderada pelos pesos)
        ...

    Depois:
      - converte distâncias em similaridades (0–100),
      - monta a lista 'resultados',
      - e ao final faz um pós-processamento para:
          * manter somente os endereços com MAIOR similaridade_final por idx_df1
          * e, dentro de cada idx_df1, manter todas as linhas que tenham
            (endereco_df2, numero_df2, bairro_df2) iguais ao do melhor match.
    """
    print("entrou no llm")

    # Garante que lista de colunas é realmente lista
    if isinstance(colunas_logradouro1_original, str):
        colunas_logradouro1_original = [colunas_logradouro1_original]
    print("passou 1")
    if isinstance(colunas_logradouro2_original, str):
        colunas_logradouro2_original = [colunas_logradouro2_original]
    print("passou 2")

    # Verificações básicas
    if cod_unico_endereco is None:
        raise ValueError("É necessário informar o nome da coluna 'cod_unico_endereco' em df2.")
    print("passou 3")
    if cod_unico_endereco not in df2.columns:
        raise ValueError(f"Coluna '{cod_unico_endereco}' não encontrada em df2.")
    print("passou 4")
    if cod_unico_endereco_entrada is None:
        raise ValueError("É necessário informar o nome da coluna 'cod_unico_endereco_entrada' em df1.")

    # Mapeia cod_unico_endereco -> índice em df2 para lookup rápido
    cod_to_idx2: Dict[str, Any] = {}
    print("passou 5")
    for idx2, cod in df2[cod_unico_endereco].items():
        if pd.isna(cod):
            continue
        cod_to_idx2[str(cod)] = idx2
    print("passou 6")

    resultados: List[Dict[str, Any]] = []
    print("passou 7")

    # Abre conexão única com o banco
    conn = get_pg_connection()
    print("passou 8")
    cur = conn.cursor()
    print("passou 9")

    try:
        for idx1 in df1.index:
            cod_entrada = df1.loc[idx1, cod_unico_endereco_entrada]
            print(f"idx1={idx1} cod_entrada={cod_entrada}")

            if pd.isna(cod_entrada):
                continue

            # Busca no Postgres os top_n vizinhos (CNEFE) para o embedding da entrada (3 componentes)
            cur.execute(
                """
                SELECT
                    c.cod_unico,
                    (c.logradouro_embedding <-> e.logradouro_embedding) AS dist_log,
                    (c.numero_embedding      <-> e.numero_embedding)    AS dist_num,
                    (c.bairro_embedding      <-> e.bairro_embedding)    AS dist_bairro,
                    (%s * (c.logradouro_embedding <-> e.logradouro_embedding)
                     + %s * (c.numero_embedding   <-> e.numero_embedding)
                     + %s * (c.bairro_embedding   <-> e.bairro_embedding)) AS distancia_final
                FROM entrada_rondonia_embeddings e
                JOIN cnefe_rondonia_embeddings   c ON TRUE
                WHERE e.cod_unico = %s
                ORDER BY distancia_final
                LIMIT %s;
                """,
                (peso_logradouro, peso_numero, peso_bairro, cod_entrada, top_n),
            )
            candidatos = cur.fetchall()

            if not candidatos:
                # Nenhum embedding encontrado ou nenhum vizinho – pula registro
                continue

            for cod_unico_cnefe, dist_log, dist_num, dist_bairro, dist_final in candidatos:
                cod_unico_cnefe = str(cod_unico_cnefe)

                # Localiza índice de df2
                idx2 = cod_to_idx2.get(cod_unico_cnefe)
                if idx2 is None:
                    print(f"pulou {cod_unico_cnefe}")
                    continue

                # Converte distâncias em similaridades (0–100)
                score_log = distancia_para_similaridade(dist_log)
                score_num = distancia_para_similaridade(dist_num)
                score_bairro = distancia_para_similaridade(dist_bairro)
                score_final = distancia_para_similaridade(dist_final)

                resultados.append(
                    {
                        "idx_df1": idx1,
                        "endereco_df1": formatar_endereco(
                            df1.loc[idx1],
                            colunas_logradouro1_original
                            + ([col_bairro1_original] if col_bairro1_original else []),
                        ),
                        "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
                        "complemento_df1": (
                            formatar_endereco(df1.loc[idx1], colunas_complemento1)
                            if colunas_complemento1
                            else None
                        ),
                        "bairro_df1": (
                            df1.loc[idx1, col_bairro1_original]
                            if col_bairro1_original
                            else None
                        ),
                        "idx_df2": idx2,
                        "cod_unico_df2": df2.at[idx2, cod_unico_endereco],
                        "endereco_df2": formatar_endereco(
                            df2.loc[idx2],
                            colunas_logradouro2_original
                            + ([col_bairro2_original] if col_bairro2_original else []),
                        ),
                        "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
                        "complemento_df2": (
                            formatar_endereco(df2.loc[idx2], colunas_complemento2)
                            if colunas_complemento2
                            else None
                        ),
                        "bairro_df2": (
                            df2.loc[idx2, col_bairro2_original]
                            if col_bairro2_original
                            else None
                        ),
                        "similaridade_logradouro": round(score_log, 2),
                        "similaridade_numero": (
                            round(score_num, 2) if score_num is not None else None
                        ),
                        "similaridade_bairro": (
                            round(score_bairro, 2) if score_bairro is not None else None
                        ),
                        "similaridade_final": round(score_final, 2),
                        "latitude_verdadeira": (
                            df1.at[idx1, latitude_verdadeira]
                            if latitude_verdadeira
                            else None
                        ),
                        "longitude_verdadeira": (
                            df1.at[idx1, longitude_verdadeira]
                            if longitude_verdadeira
                            else None
                        ),
                        "cd_setor_verdadeiro": (
                            df1.at[idx1, cd_setor_verdadeiro]
                            if cd_setor_verdadeiro
                            else None
                        ),
                        "latitude_resultante": (
                            df2.at[idx2, latitude_resultante]
                            if latitude_resultante
                            else None
                        ),
                        "longitude_resultante": (
                            df2.at[idx2, longitude_resultante]
                            if longitude_resultante
                            else None
                        ),
                        "cd_setor_resultante": (
                            df2.at[idx2, cd_setor_resultante]
                            if cd_setor_resultante
                            else None
                        ),
                    }
                )

    finally:
        cur.close()
        conn.close()

    # ---------------- PÓS-PROCESSAMENTO ----------------
    # Mantém apenas:
    #  - o(s) match(es) com MAIOR similaridade_final por idx_df1
    #  - e, para cada idx_df1, todas as linhas que tenham o MESMO
    #    (endereco_df2, numero_df2, bairro_df2) do melhor match.
    print("----------------RESULTADOS (BRUTOS)-----------------")
    print(resultados[:10])  # só primeiros 10 pra não explodir log
    print("----------------------------------------------------")

    df_resultados = pd.DataFrame(resultados)
    if df_resultados.empty:
        return df_resultados

    grupos_filtrados = []

    for idx_df1, grupo in df_resultados.groupby("idx_df1"):
        # Maior similaridade_final para esse idx_df1
        max_sim = grupo["similaridade_final"].max()

        # Linhas com esse max_sim (pode haver empate)
        melhores = grupo[grupo["similaridade_final"] == max_sim]

        # Escolhe uma linha de referência (primeira)
        ref = melhores.iloc[0]

        # Filtra o grupo para manter todas as linhas cujo
        # (endereco_df2, numero_df2, bairro_df2) sejam iguais à referência
        mask = (
            (grupo["endereco_df2"] == ref["endereco_df2"]) &
            (grupo["numero_df2"] == ref["numero_df2"]) &
            (grupo["bairro_df2"] == ref["bairro_df2"])
        )
        grupo_filtrado = grupo[mask]
        grupos_filtrados.append(grupo_filtrado)

    df_final = pd.concat(grupos_filtrados, ignore_index=True)

    return df_final
