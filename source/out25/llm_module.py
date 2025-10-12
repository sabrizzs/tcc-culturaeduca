import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from comparador import montar_logradouro, normalize_bairro, formatar_endereco
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)


def executar_llm(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    top_n=5,
    peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
    **kwargs
):
    """Compara endereços entre dois DataFrames usando embeddings (LLM)."""

    df1 = df1.copy()
    df2 = df2.copy()

    # --- Garantir que listas sejam listas mesmo se vier string ---
    def ensure_list(x):
        if x is None:
            return []
        if isinstance(x, str):
            return [x]
        return list(x)

    colunas_logradouro1 = ensure_list(colunas_logradouro1)
    colunas_logradouro2 = ensure_list(colunas_logradouro2)
    col_bairro1 = ensure_list(col_bairro1)
    col_bairro2 = ensure_list(col_bairro2)

    # --- Montar logradouro normalizado ---
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

    # --- Normalizar bairros ---
    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    # --- Gerar embeddings ---
    emb1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_numpy=True)
    emb2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_numpy=True)

    resultados = []

    # --- Função auxiliar para converter número ---
    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except:
            return None

    # ============================================================
    # LOOP PRINCIPAL
    # ============================================================
    for idx1, e1 in enumerate(emb1):
        cos_sim = cosine_similarity([e1], emb2)[0]
        num1 = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        matches = []

        for idx2, score_log in enumerate(cos_sim):
            num2 = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # --- Similaridade de número ---
            if num1 is not None and num2 is not None:
                diff = abs(num1 - num2)
                score_num = 1.0 if diff == 0 else max(0, 1 - diff / max(num1, num2))
            else:
                score_num = None

            # --- Similaridade de bairro ---
            b1_text = str(bairro1 or "")
            b2_text = str(bairro2 or "")
            if b1_text or b2_text:
                emb_b1 = model.encode([b1_text])
                emb_b2 = model.encode([b2_text])
                score_bairro = cosine_similarity(emb_b1, emb_b2)[0][0]
            else:
                score_bairro = None

            # --- Score Final ---
            score_final = (
                score_log * peso_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordenar por score final
        matches.sort(key=lambda x: x[4], reverse=True)
        idx2_best, sc_log, sc_num, sc_bai, sc_final = matches[0]

        # ============================================================
        # FORMATAR ENDEREÇOS E SUGESTÕES
        # ============================================================
        end1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1)
        end2 = formatar_endereco(df2.loc[idx2_best], colunas_logradouro2)

        # Montar topN
        sugestoes = []
        for idx2_sug, sc_log_s, sc_num_s, sc_bai_s, sc_final_s in matches[:top_n]:
            end_sug = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2)
            sugestoes.append(f"{end_sug} | Score Final: {sc_final_s*100:.2f}")

        # ============================================================
        # SALVAR RESULTADOS
        # ============================================================
        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": end1,
            "numero_df1": df1.loc[idx1, col_num1] if col_num1 else "",
            "bairro_df1": bairro1,
            "idx_df2": idx2_best,
            "endereco_df2": end2,
            "numero_df2": df2.loc[idx2_best, col_num2] if col_num2 else "",
            "bairro_df2": df2.loc[idx2_best, "bairro_normalizado"],
            "similaridade_logradouro": round(sc_log * 100, 2),
            "similaridade_numero": round(sc_num * 100, 2) if sc_num is not None else "",
            "similaridade_bairro": round(sc_bai * 100, 2) if sc_bai is not None else "",
            "similaridade_final": round(sc_final * 100, 2),
            "sugestoes_topN": "; ".join(sugestoes)
        })

    return pd.DataFrame(resultados)
