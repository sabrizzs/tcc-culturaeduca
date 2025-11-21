import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from comparador import montar_logradouro, normalize_bairro, formatar_endereco

# -------------------------------------------------------------------
# Cache global do modelo
# -------------------------------------------------------------------
_MODEL = None
_DEVICE = None


def _get_model():
    global _MODEL, _DEVICE
    if _MODEL is None:
        _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _MODEL = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device=_DEVICE,
        )
    return _MODEL


def executar_llm(
    df1,
    df2,
    colunas_logradouro1,
    colunas_logradouro2,
    col_num1=None,
    col_num2=None,
    col_bairro1=None,
    col_bairro2=None,
    top_n=5,
    peso_logradouro=0.5,
    peso_numero=0.4,
    peso_bairro=0.1,
    batch_tamanho_df1=64,   # <- processar df1 "em partes"
    **kwargs,
):
    """
    Versão em "pedaços": processa os endereços de df1 em lotes (batch_tamanho_df1),
    mas matematicamente calcula os mesmos scores que a versão linha a linha.
    """

    # ----------------------- helpers -----------------------
    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except Exception:
            return None

    def limpar_bairro_llm(b):
        if not isinstance(b, str):
            b = "" if pd.isna(b) else str(b)
        for termo in ["jardim", "jd", "vila", "vl", "bairro", "jd.", "vl.", "pq.", "parque"]:
            b = b.replace(termo, "")
        return b.strip()

    # ---------------- modelo + cópias ----------------------
    model = _get_model()
    df1 = df1.copy()
    df2 = df2.copy()

    # Normalização (reaproveitando se já tiver)
    if "logradouro_normalizado" not in df1.columns:
        df1["logradouro_normalizado"] = montar_logradouro(
            df1, colunas_logradouro1, excluir_col_num=col_num1
        )
    if "logradouro_normalizado" not in df2.columns:
        df2["logradouro_normalizado"] = montar_logradouro(
            df2, colunas_logradouro2, excluir_col_num=col_num2
        )

    if "bairro_normalizado" not in df1.columns:
        df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    if "bairro_normalizado" not in df2.columns:
        df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    if "bairro_original" not in df1.columns:
        df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
    if "bairro_original" not in df2.columns:
        df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

    df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
    df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

    # ---------------- embeddings ----------------
    emb1 = model.encode(
        df1["logradouro_normalizado"].tolist(),
        convert_to_tensor=True,
        batch_size=64,
        show_progress_bar=False,
    )
    emb2 = model.encode(
        df2["logradouro_normalizado"].tolist(),
        convert_to_tensor=True,
        batch_size=64,
        show_progress_bar=False,
    )

    usa_bairro = bool(col_bairro1 or col_bairro2)
    if usa_bairro:
        emb_bairros1 = model.encode(
            df1["bairro_normalizado"].tolist(),
            convert_to_tensor=True,
            batch_size=64,
            show_progress_bar=False,
        )
        emb_bairros2 = model.encode(
            df2["bairro_normalizado"].tolist(),
            convert_to_tensor=True,
            batch_size=64,
            show_progress_bar=False,
        )
    else:
        emb_bairros1 = emb_bairros2 = None

    n1 = len(df1)
    n2 = len(df2)

    # ---------------- pré-cálculos em lista ----------------
    if col_num1:
        numeros1_orig = df1[col_num1].tolist()
        numeros1_int = [try_int(x) for x in numeros1_orig]
    else:
        numeros1_orig = [None] * n1
        numeros1_int = [None] * n1

    if col_num2:
        numeros2_orig = df2[col_num2].tolist()
        numeros2_int = [try_int(x) for x in numeros2_orig]
    else:
        numeros2_orig = [None] * n2
        numeros2_int = [None] * n2

    bairros_orig1 = df1["bairro_original"].tolist()
    bairros_orig2 = df2["bairro_original"].tolist()
    bairros_norm1 = df1["bairro_normalizado"].tolist()
    bairros_norm2 = df2["bairro_normalizado"].tolist()

    cols_fmt1 = colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])
    cols_fmt2 = colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])

    enderecos1_fmt = [formatar_endereco(df1.iloc[i], cols_fmt1) for i in range(n1)]
    enderecos2_fmt = [formatar_endereco(df2.iloc[j], cols_fmt2) for j in range(n2)]

    tol = float(kwargs.get("tolerancia_logradouro", 0.001))
    preferir_numero_exato = True
    margem_override = 8

    resultados = []

    # ---------------- loop em "pedaços" de df1 ----------------
    for start in range(0, n1, batch_tamanho_df1):
        end = min(start + batch_tamanho_df1, n1)
        batch_size = end - start

        # Lote de embeddings de df1
        emb1_batch = emb1[start:end]
        # Similaridade de logradouro: (batch_size, n2)
        cos_matrix_log = util.cos_sim(emb1_batch, emb2)

        if usa_bairro:
            emb_bairros1_batch = emb_bairros1[start:end]
            cos_matrix_bairro = util.cos_sim(emb_bairros1_batch, emb_bairros2)
        else:
            cos_matrix_bairro = None

        # Agora, linha a linha dentro do lote (mas reaproveitando a matrix)
        for offset in range(batch_size):
            idx1 = start + offset
            cos_scores = cos_matrix_log[offset]

            max_score = float(cos_scores.max().item())
            mask = cos_scores >= (max_score - tol)
            idxs_candidatos = torch.nonzero(mask, as_tuple=False).flatten().tolist()

            num1_int = numeros1_int[idx1]
            bairro1_norm = bairros_norm1[idx1]

            matches_final = []

            for idx2 in idxs_candidatos:
                score_log = float(cos_scores[idx2].item()) * 100.0

                num2_int = numeros2_int[idx2]
                bairro2_norm = bairros_norm2[idx2]

                # similaridade de número (igual à lógica original)
                if num1_int is not None and num2_int is not None:
                    diff = abs(num1_int - num2_int)
                    if diff == 0:
                        score_num = 100.0
                    else:
                        maior = max(num1_int, num2_int)
                        score_num = max(0.0, 100.0 * (1 - diff / maior)) if maior else 0.0
                else:
                    score_num = None

                # similaridade de bairro
                if usa_bairro and (bairro1_norm or bairro2_norm):
                    score_bairro = float(
                        cos_matrix_bairro[offset, idx2].item()
                    ) * 100.0
                else:
                    score_bairro = None

                num_component = score_num if score_num is not None else score_log
                bairro_component = score_bairro if score_bairro is not None else score_log
                score_final = (
                    score_log * peso_logradouro
                    + num_component * peso_numero
                    + bairro_component * peso_bairro
                )

                matches_final.append(
                    (idx2, score_log, score_num, score_bairro, score_final)
                )

            if not matches_final:
                continue

            # ordena por score final
            matches_final.sort(key=lambda x: x[4], reverse=True)
            melhor_atual = matches_final[0]

            # override de número 100, mesma lógica
            if preferir_numero_exato:
                candidatos_exatos = [m for m in matches_final if m[2] == 100]
                if candidatos_exatos:
                    melhor_exato = max(
                        candidatos_exatos, key=lambda x: (x[1], x[4])
                    )
                    if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                        matches_final.remove(melhor_exato)
                        matches_final.insert(0, melhor_exato)

            idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

            # top N sugestões
            sugestoes_formatadas = []
            for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
                numero_sug = numeros2_orig[idx2_sug] if col_num2 else ""
                endereco_sug = enderecos2_fmt[idx2_sug]
                sugestoes_formatadas.append(
                    f"{endereco_sug} {numero_sug} | Score Final: {sc_final:.2f}"
                )

            resultados.append(
                {
                    "idx_df1": idx1,
                    "endereco_df1": enderecos1_fmt[idx1],
                    "numero_df1": numeros1_orig[idx1],
                    "bairro_df1": bairros_orig1[idx1],
                    "idx_df2": idx2,
                    "endereco_df2": enderecos2_fmt[idx2],
                    "numero_df2": numeros2_orig[idx2],
                    "bairro_df2": bairros_orig2[idx2],
                    "similaridade_logradouro": round(score_log, 2),
                    "similaridade_numero": round(score_num, 2)
                    if score_num is not None
                    else None,
                    "similaridade_bairro": round(score_bairro, 2)
                    if score_bairro is not None
                    else None,
                    "similaridade_final": round(melhor_final, 2),
                    "sugestoes_topN": "; ".join(sugestoes_formatadas),
                }
            )

    return pd.DataFrame(resultados)
