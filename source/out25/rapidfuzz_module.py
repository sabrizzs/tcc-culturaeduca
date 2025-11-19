# rapidfuzz.py
import pandas as pd
from rapidfuzz import process, fuzz
from comparador import montar_logradouro, normalize_bairro, formatar_endereco

def executar_rapidfuzz(df1, df2,
                        colunas_logradouro1, colunas_logradouro2,
                        col_num1=None, col_num2=None,
                        col_bairro1=None, col_bairro2=None,
                        top_n=5,
                        peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
                        **kwargs):
    limiar_similaridade = kwargs.get("limiar_similaridade", 85)

    """
    Compara endereços usando a biblioteca RapidFuzz.

    - O RapidFuzz calcula a similaridade entre textos com base na 
      semelhança de caracteres (distância de Levenshtein).  
      Exemplo: "Rua das Flores" ≈ "Rua das Flôres" ≈ "R das Flores".

    - Cada texto recebe uma pontuação de 0 a 100, onde 100 significa
      idêntico e 0 totalmente diferente.

    - O algoritmo combina três critérios:
        - Nome da rua (logradouro)
        - Número do endereço (comparado numericamente)
        - Bairro (comparado textualmente)

    Retorna:
        Um DataFrame com os melhores matches e as top N sugestões.
    """

    # Cria cópias das tabelas originais
    df1 = df1.copy()
    df2 = df2.copy()

    # Normaliza os endereços
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

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
        except:
            return None

    # Loop principal: compara cada endereço de df1 com todos de df2
    for idx1, endereco1 in df1["logradouro_normalizado"].items():

        # process.extract faz a comparação fuzzy entre uma string e
        # uma lista de strings, retornando uma lista de matches com:
        # (texto_comparado, pontuação, índice_no_df2)
        matches_all = process.extract(
            endereco1,
            df2["logradouro_normalizado"],
            scorer=fuzz.token_set_ratio,
            limit=None
        )

        num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        matches_final = []

        # Para cada possível correspondência encontrada:
        # calcula a pontuação detalhada e o score final
        for log2_texto, score_log, idx2 in matches_all:
            num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # O número do endereço é comparado de forma quantitativa
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                score_num = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_num = None

            # Similaridade bairro
            score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if bairro1 or bairro2 else None

            # Soma ponderada dos scores
            score_final = (
                score_log * peso_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordena os candidatos e escolhe o melhor match
        matches_final.sort(key=lambda x: x[4], reverse=True)

        # Override para número exato:
        # se houver número exato (100%), prioriza esse
        preferir_numero_exato = True
        margem_override = 8 # tolerância para substituir o melhor caso
        if preferir_numero_exato:
            candidatos_exatos = [m for m in matches_final if m[2] == 100]
            if candidatos_exatos:
                melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
                melhor_atual = matches_final[0]
                if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                    matches_final.remove(melhor_exato)
                    matches_final.insert(0, melhor_exato)

        # Melhor match
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # Monta uma lista de sugestões (top N endereços mais parecidos)
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(
                df2.loc[idx2_sug],
                colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
            )
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.0f}")

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
