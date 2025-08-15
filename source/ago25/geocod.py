#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from rapidfuzz import process, fuzz
import unidecode
from datetime import datetime

SEPARADOR = ";"

def normalize(text: str) -> str:
    if pd.isna(text):
        return ""
    return unidecode.unidecode(str(text)).strip().lower()

def normalizar_abreviacoes(texto: str) -> str:
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
    texto = f" {texto} "
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()

def carregar_e_tratar_csv(caminho: str, colunas: list) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=SEPARADOR, dtype=str)

    df["endereco_original"] = df[colunas].fillna("").agg(" ".join, axis=1).apply(normalize)
    df["endereco_normalizado"] = df["endereco_original"].apply(normalizar_abreviacoes)
    return df

def comparar_enderecos(df1: pd.DataFrame, df2: pd.DataFrame, limiar=85, top_n=5) -> pd.DataFrame:
    resultados = []

    for idx1, row1 in df1.iterrows():
        endereco1 = row1["endereco_normalizado"]
        endereco1_original = row1["endereco_original"]

        match, score, idx2 = process.extractOne(
            endereco1,
            df2["endereco_normalizado"],
            scorer=fuzz.token_set_ratio
        )

        endereco2_original = df2.loc[idx2, "endereco_original"]

        sugestoes_top = ""
        if score < limiar:
            matches_top = process.extract(
                endereco1,
                df2["endereco_normalizado"],
                scorer=fuzz.token_set_ratio,
                limit=top_n
            )
            sugestoes_formatadas = [
                f"{df2.loc[idx, 'endereco_original']} ({sim_score:.0f})"
                for _, sim_score, idx in matches_top
            ]
            sugestoes_top = "; ".join(sugestoes_formatadas)

        resultados.append({
            "idx_base1": idx1,
            "endereco_base1": endereco1_original,
            "idx_base2": idx2,
            "endereco_base2": endereco2_original,
            "similaridade": score,
            "sugestoes_top": sugestoes_top
        })

    return pd.DataFrame(resultados)

def salvar_csv(df: pd.DataFrame, prefixo_nome: str) -> str:
    id_datahora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{prefixo_nome}_{id_datahora}.csv"
    df.to_csv(nome_arquivo, sep=SEPARADOR, index=False)
    return nome_arquivo
