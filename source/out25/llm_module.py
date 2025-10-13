# llm_module.py
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from comparador import montar_logradouro, normalize_bairro, formatar_endereco

def executar_llm(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    top_n=5,
    peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
    **kwargs
):
    """
    Compara endereços usando embeddings de linguagem (open source, via Hugging Face).
    Retorna DataFrame com melhores matches e top N sugestões.
    """

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)

    df1 = df1.copy()
    df2 = df2.copy()

    # Normalização
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)
    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    # Cria embeddings
    emb1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)
    emb2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)

    resultados = []

    def try_int(n):
        if pd.isna(n): return None
        try: return int(float(n))
        except: return None

    for idx1, endereco1 in enumerate(df1["logradouro_normalizado"]):
        # Similaridade de logradouro via embeddings
        cos_scores = util.cos_sim(emb1[idx1], emb2)[0]
        top_results = torch.topk(cos_scores, k=min(top_n*5, len(df2)))  # busca mais candidatos

        num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        matches_final = []
        for score, idx2 in zip(top_results.values, top_results.indices):
            idx2 = int(idx2)
            score_log = float(score.item()) * 100
            num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # Similaridade numérica
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                score_num = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_num = score_log

            # Similaridade bairro (texto)
            if bairro1 or bairro2:
                emb_b1 = model.encode([bairro1 or ""], convert_to_tensor=True)
                emb_b2 = model.encode([bairro2 or ""], convert_to_tensor=True)
                score_bairro = float(util.cos_sim(emb_b1, emb_b2).item()) * 100
            else:
                score_bairro = score_log

            # Score final ponderado
            score_final = (
                score_log * peso_logradouro +
                score_num * peso_numero +
                score_bairro * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordena
        matches_final.sort(key=lambda x: x[4], reverse=True)

        # Melhor match
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # Top N sugestões
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(
                df2.loc[idx2_sug],
                colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
            )
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.2f}")

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
            "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
            "bairro_df1": bairro1,
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])),
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
            "bairro_df2": df2.loc[idx2, "bairro_normalizado"],
            "similaridade_logradouro": round(score_log, 2),
            "similaridade_numero": round(score_num, 2),
            "similaridade_bairro": round(score_bairro, 2),
            "similaridade_final": round(melhor_final, 2),
            "sugestoes_topN": "; ".join(sugestoes_formatadas)
        })

    return pd.DataFrame(resultados)
