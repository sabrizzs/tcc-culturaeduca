# llm_module.py
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from comparador import montar_logradouro, normalize_bairro, formatar_endereco
from sentence_transformers import SentenceTransformer

"""
llm_module.py - Comparação de endereços usando embeddings (LLM)
Responsabilidades:
1. Gerar embeddings dos endereços usando modelos de linguagem.
2. Calcular similaridade via cosine similarity.
3. Aplicar pontuação ponderada (logradouro, número, bairro).
4. Retornar top N e melhor match, igual ao rapidfuzz_module.
"""

MODEL_NAME = "all-MiniLM-L6-v2"  # Modelo leve e eficiente para embeddings
model = SentenceTransformer(MODEL_NAME)

def executar_llm(df1, df2,
                 colunas_logradouro1, colunas_logradouro2,
                 col_num1=None, col_num2=None,
                 col_bairro1=None, col_bairro2=None,
                 top_n=5,
                 peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
                 **kwargs):
    
    df1 = df1.copy()
    df2 = df2.copy()

    # Garante que colunas sejam listas
    def ensure_list(col):
        if col is None:
            return []
        if isinstance(col, str):
            return [col]
        if isinstance(col, list):
            return col
        return list(col) 

    colunas_logradouro1 = ensure_list(colunas_logradouro1)
    colunas_logradouro2 = ensure_list(colunas_logradouro2)
    col_bairro1 = ensure_list(col_bairro1)
    col_bairro2 = ensure_list(col_bairro2)

    # Normalização dos logradouros e bairros
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    # Gera embeddings dos logradouros
    embeddings1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_numpy=True)
    embeddings2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_numpy=True)

    resultados = []

    # Função auxiliar para tratar números
    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except:
            return None

    # Para cada endereço do df1
    for idx1, emb1 in enumerate(embeddings1):
        num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        # Calcula similaridade cosine com todos do df2
        cos_sim = cosine_similarity([emb1], embeddings2)[0]

        matches_final = []

        for idx2, score_log in enumerate(cos_sim):
            num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # Similaridade numérica (igual ao RapidFuzz)
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                score_num = 1.0 if diff == 0 else max(0, 1 - diff / max(num1_int, num2_int))
            else:
                score_num = None

            # Similaridade de bairro usando embeddings, evitando NaN
            bairro1_texto = str(bairro1) if pd.notna(bairro1) else ""
            bairro2_texto = str(bairro2) if pd.notna(bairro2) else ""

            if bairro1_texto or bairro2_texto:
                score_bairro = cosine_similarity(
                    model.encode([bairro1_texto]), model.encode([bairro2_texto])
                )[0][0]
            else:
                score_bairro = None

            # Score final ponderado
            score_final = (
                score_log * peso_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordena pelo score final
        matches_final.sort(key=lambda x: x[4], reverse=True)

        # Melhor match
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # -------------------
        # Top N sugestões
        # -------------------
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            colunas_para_formatar = colunas_logradouro2.copy()
            if col_bairro2:
                colunas_para_formatar.append(col_bairro2)

            endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas_para_formatar)
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final*100:.2f}")

        # Cria dicionário de resultados
        colunas_para_formatar_df1 = colunas_logradouro1.copy()
        if col_bairro1:
            colunas_para_formatar_df1.append(col_bairro1)

        colunas_para_formatar_df2 = colunas_logradouro2.copy()
        if col_bairro2:
            colunas_para_formatar_df2.append(col_bairro2)

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_para_formatar_df1),
            "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
            "bairro_df1": bairro1,
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_para_formatar_df2),
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
            "bairro_df2": df2.loc[idx2, "bairro_normalizado"],
            "similaridade_logradouro": round(score_log*100, 2),
            "similaridade_numero": round(score_num*100, 2) if score_num is not None else None,
            "similaridade_bairro": round(score_bairro*100, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_final*100, 2),
            "sugestoes_topN": "; ".join(sugestoes_formatadas)
        })

    return pd.DataFrame(resultados)
