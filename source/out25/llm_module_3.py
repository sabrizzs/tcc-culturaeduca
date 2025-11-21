import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from comparador import montar_logradouro, normalize_bairro, formatar_endereco

# -------------------------------------------------------------------
# Cache simples do modelo (não recarrega a cada chamada)
# -------------------------------------------------------------------
_MODEL = None
_DEVICE = None


def _get_model():
    global _MODEL, _DEVICE
    if _MODEL is None:
        _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _MODEL = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device=_DEVICE
        )
    return _MODEL


def executar_llm(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    top_n=5,
    peso_logradouro=0.5,
    peso_numero=0.4,
    peso_bairro=0.1,
    **kwargs
):
    """
    Mesma lógica do seu executar_llm original, mas com:
    - reaproveitamento de normalização feita no comparador
    - cache do modelo
    - menos trabalho repetido dentro dos loops
    """

    def try_int(n):
        """
        Tenta converter um valor em número inteiro.
        Retorna None se não for possível (exemplo: texto vazio).
        (Mesma lógica que você tinha aqui dentro.)
        """
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except Exception:
            return None

    def limpar_bairro_llm(b):
        for termo in ["jardim", "jd", "vila", "vl", "bairro", "jd.", "vl.", "pq.", "parque"]:
            b = b.replace(termo, "")
        return b.strip()

    # Carrega / reutiliza o modelo
    model = _get_model()

    # Cria cópias das tabelas originais
    df1 = df1.copy()
    df2 = df2.copy()

    # ------------------------------------------------------------------
    # 1) Normalização de logradouro/bairro
    #    - Se já veio pronto do comparador.preparar_dataframe, reaproveita
    #    - Se for chamado direto (df cru), calcula aqui
    # ------------------------------------------------------------------
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

    # Mantém cópia dos bairros originais (para exibir no resultado final)
    df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
    df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

    # Remove termos genéricos que atrapalham a similaridade semântica
    df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
    df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

    # ------------------------------------------------------------------
    # 2) Geração de embeddings
    # ------------------------------------------------------------------
    emb1 = model.encode(
        df1["logradouro_normalizado"].tolist(),
        convert_to_tensor=True,
        show_progress_bar=False,   # desliga progress bar (mais leve)
    )
    emb2 = model.encode(
        df2["logradouro_normalizado"].tolist(),
        convert_to_tensor=True,
        show_progress_bar=False,
    )

    usa_bairro = (col_bairro1 is not None) or (col_bairro2 is not None)
    if usa_bairro:
        emb_bairros1 = model.encode(
            df1["bairro_normalizado"].tolist(),
            convert_to_tensor=True
        )
        emb_bairros2 = model.encode(
            df2["bairro_normalizado"].tolist(),
            convert_to_tensor=True
        )
    else:
        emb_bairros1 = None
        emb_bairros2 = None

    # ------------------------------------------------------------------
    # 3) Pré-cálculo de colunas usadas em loop (evita .loc repetido)
    # ------------------------------------------------------------------
    n1 = len(df1)
    n2 = len(df2)

    if col_num2:
        numeros2_orig = df2[col_num2].tolist()
        numeros2_int = [try_int(x) for x in numeros2_orig]
    else:
        numeros2_orig = None
        numeros2_int = None

    if col_num1:
        numeros1_orig = df1[col_num1].tolist()
    else:
        numeros1_orig = None

    bairros_norm1 = df1["bairro_normalizado"].tolist()
    bairros_norm2 = df2["bairro_normalizado"].tolist()

    tol = float(kwargs.get("tolerancia_logradouro", 0.001))
    preferir_numero_exato = True
    margem_override = 8  # mesma lógica

    resultados = []

    # ------------------------------------------------------------------
    # 4) Loop principal (mesma lógica de antes, só com menos overhead)
    # ------------------------------------------------------------------
    for idx1 in range(n1):
        # Similaridade de logradouro entre um endereço de df1 e todos de df2
        cos_scores = util.cos_sim(emb1[idx1], emb2)[0]

        max_score = float(cos_scores.max().item())
        mask = cos_scores >= (max_score - tol)
        idxs_candidatos = torch.nonzero(mask).flatten().tolist()

        num1_int = try_int(numeros1_orig[idx1]) if col_num1 else None
        bairro1 = bairros_norm1[idx1]

        matches_final = []

        # Para cada endereço candidato (df2), calcula as pontuações
        for idx2 in idxs_candidatos:
            score_log = float(cos_scores[idx2].item()) * 100  # 0..100

            num2_int = numeros2_int[idx2] if col_num2 else None
            bairro2 = bairros_norm2[idx2]

            # Similaridade de número (igual à lógica original)
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_num = 100
                else:
                    maior = max(num1_int, num2_int)
                    score_num = max(0, 100 * (1 - diff / maior)) if maior else 0
            else:
                score_num = None

            # Similaridade de bairro (mesma lógica de antes)
            if usa_bairro and (bairro1 or bairro2):
                score_bairro = float(
                    util.cos_sim(emb_bairros1[idx1], emb_bairros2[idx2]).item()
                ) * 100
            else:
                score_bairro = None

            # Soma ponderada dos scores (sem mudar pesos)
            num_component = score_num if score_num is not None else score_log
            bairro_component = score_bairro if score_bairro is not None else score_log
            score_final = (
                score_log * peso_logradouro +
                num_component * peso_numero +
                bairro_component * peso_bairro
            )

            matches_final.append(
                (idx2, score_log, score_num, score_bairro, score_final)
            )

        if not matches_final:
            continue

        # Ordena pelos scores finais
        matches_final.sort(key=lambda x: x[4], reverse=True)
        melhor_atual = matches_final[0]

        # Override para número exato (mesma regra)
        if preferir_numero_exato:
            candidatos_exatos = [m for m in matches_final if m[2] == 100]
            if candidatos_exatos:
                melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
                if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                    matches_final.remove(melhor_exato)
                    matches_final.insert(0, melhor_exato)

        # Melhor match
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # Monta lista de sugestões (top N)
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(
                df2.loc[idx2_sug],
                colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
            )
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(
                f"{endereco_original} {numero} | Score Final: {sc_final:.2f}"
            )

        # Salva o resultado consolidado
        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(
                df1.loc[idx1],
                colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])
            ),
            "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
            "bairro_df1": df1.loc[idx1, "bairro_original"],
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(
                df2.loc[idx2],
                colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
            ),
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
            "bairro_df2": df2.loc[idx2, "bairro_original"],
            "similaridade_logradouro": round(score_log, 2),
            "similaridade_numero": round(score_num, 2) if score_num is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_final, 2),
            "sugestoes_topN": "; ".join(sugestoes_formatadas)
        })

    return pd.DataFrame(resultados)
