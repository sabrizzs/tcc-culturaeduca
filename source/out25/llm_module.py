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
    peso_logradouro=0.5,
    peso_numero=0.4,
    peso_bairro=0.1,
    **kwargs
):

    """
    Compara endereços usando embeddings de linguagem (resultado numérico da LLM)  
    (open source, modelo da Hugging Face)

    - Modelo usado: "all-MiniLM-L6-v2"
        Rede neural treinada em milhões de textos que entende o significado 
        das palavras — por exemplo, "Av. Paulista" ≈ "Avenida Paulista".

    - Embeddings:
        Cada frase é convertida em um vetor numérico (ex: [0.13, -0.44, 0.95, ...]) 
        que representa seu sentido. Frases semelhantes geram vetores próximos.

        A similaridade entre dois textos é calculada pelo cosseno entre os vetores:
            1.0 → idênticos, 0.8 → parecidos, 0.2 → diferentes.

    Retorna:
        Um DataFrame com os melhores matches entre endereços e as top N sugestões.
    """

    # Define onde o modelo vai rodar: CPU ou GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Carrega o modelo de linguagem
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)

    # Cria cópias das tabelas originais
    df1 = df1.copy()
    df2 = df2.copy()

    # Normaliza os endereços
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)
    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    # Gera os embeddings (vetores numéricos) para os logradouros
    # Quanto mais próximos dois vetores, mais semelhantes são os textos.
    emb1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)
    emb2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)

    emb_bairros1 = model.encode(df1["bairro_normalizado"].tolist(), convert_to_tensor=True)
    emb_bairros2 = model.encode(df2["bairro_normalizado"].tolist(), convert_to_tensor=True)

    resultados = []

    def try_int(n):
        """
        Tenta converter um valor em número inteiro.
        Retorna None se não for possível (exemplo: texto vazio).
        """
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except Exception:
            return None

    # Loop principal: compara cada endereço de df1 com todos de df2
    for idx1, _ in enumerate(df1["logradouro_normalizado"]):

        # Calcula a similaridade entre o embedding do endereço de df1
        # e todos os embeddings de df2, usando "cosine similarity".
        # Essa medida vai de 0 (muito diferente) a 1 (muito parecido).
        cos_scores = util.cos_sim(emb1[idx1], emb2)[0]

        # Ordena os índices dos endereços de df2 do mais parecido para o menos parecido
        indices_ordenados = torch.argsort(cos_scores, descending=True)

        # Extrai número e bairro do endereço atual de df1
        num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        matches_final = []

        # Para cada endereço candidato (df2), calcula as pontuações
        for idx2_tensor in indices_ordenados:
            idx2 = int(idx2_tensor.item())
            score_log = float(cos_scores[idx2].item()) * 100
            num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # O número do endereço é comparado de forma quantitativa
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_num = 100
                else:
                    maior = max(num1_int, num2_int)
                    score_num = max(0, 100 * (1 - diff / maior)) if maior else 0
            else:
                score_num = None

            # Os bairros também viram embeddings, e a similaridade é medida
            # pelo cosseno entre os vetores, da mesma forma que os logradouros
            if bairro1 or bairro2:
                score_bairro = float(util.cos_sim(emb_bairros1[idx1], emb_bairros2[idx2]).item()) * 100
            else:
                score_bairro = None

            # Soma ponderada dos scores
            num_component = score_num if score_num is not None else score_log
            bairro_component = score_bairro if score_bairro is not None else score_log
            score_final = (
                score_log * peso_logradouro +
                num_component * peso_numero +
                bairro_component * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordena os candidatos e escolhe o melhor match
        matches_final.sort(key=lambda x: x[4], reverse=True)
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # Monta uma lista de sugestões (top N endereços mais parecidos)
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(
                df2.loc[idx2_sug],
                colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
            )
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.2f}")

        # Salva o resultado consolidado
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
            "similaridade_numero": round(score_num, 2) if score_num is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_final, 2),
            "sugestoes_topN": "; ".join(sugestoes_formatadas)
        })

    return pd.DataFrame(resultados)
