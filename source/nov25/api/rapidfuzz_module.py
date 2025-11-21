# # rapidfuzz.py
# import pandas as pd
# from rapidfuzz import process, fuzz
# from comparador import montar_logradouro, normalize_bairro, formatar_endereco

# def executar_rapidfuzz(df1, df2,
#                         colunas_logradouro1, colunas_logradouro2,
#                         col_num1=None, col_num2=None,
#                         col_bairro1=None, col_bairro2=None,
#                         latitude=None, longitude=None, cd_setor=None,
#                         top_n=5,
#                         peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#                         **kwargs):
#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     """
#     Compara endereços usando a biblioteca RapidFuzz.

#     - O RapidFuzz calcula a similaridade entre textos com base na 
#       semelhança de caracteres (distância de Levenshtein).  
#       Exemplo: "Rua das Flores" ≈ "Rua das Flôres" ≈ "R das Flores".

#     - Cada texto recebe uma pontuação de 0 a 100, onde 100 significa
#       idêntico e 0 totalmente diferente.

#     - O algoritmo combina três critérios:
#         - Nome da rua (logradouro)
#         - Número do endereço (comparado numericamente)
#         - Bairro (comparado textualmente)

#     Retorna:
#         Um DataFrame com os melhores matches e as top N sugestões.
#     """

#     # Cria cópias das tabelas originais
#     df1 = df1.copy()
#     df2 = df2.copy()

#     # Normaliza os endereços
#     df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
#     df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

#     df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
#     df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

#     resultados = []

#     def try_int(n):
#         """
#         Tenta converter um valor em número inteiro.
#         Retorna None se não for possível (exemplo: texto vazio).
#         """
#         if pd.isna(n):
#             return None
#         try:
#             return int(float(n))
#         except:
#             return None

#     # Loop principal: compara cada endereço de df1 com todos de df2
#     for idx1, endereco1 in df1["logradouro_normalizado"].items():

#         # process.extract faz a comparação fuzzy entre uma string e
#         # uma lista de strings, retornando uma lista de matches com:
#         # (texto_comparado, pontuação, índice_no_df2)
#         matches_all = process.extract(
#             endereco1,
#             df2["logradouro_normalizado"],
#             scorer=fuzz.token_set_ratio,
#             limit=None
#         )

#         num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
#         bairro1 = df1.loc[idx1, "bairro_normalizado"]

#         matches_final = []

#         # Para cada possível correspondência encontrada:
#         # calcula a pontuação detalhada e o score final
#         for log2_texto, score_log, idx2 in matches_all:
#             num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
#             bairro2 = df2.loc[idx2, "bairro_normalizado"]

#             # O número do endereço é comparado de forma quantitativa
#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 score_num = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1_int, num2_int)))
#             else:
#                 score_num = None

#             # Similaridade bairro
#             score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if bairro1 or bairro2 else None

#             # Soma ponderada dos scores
#             score_final = (
#                 score_log * peso_logradouro +
#                 (score_num if score_num is not None else score_log) * peso_numero +
#                 (score_bairro if score_bairro is not None else score_log) * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         # Ordena os candidatos e escolhe o melhor match
#         matches_final.sort(key=lambda x: x[4], reverse=True)

#         # Override para número exato:
#         # se houver número exato (100%), prioriza esse
#         # Isso ajuda a corrigir casos de ruas iguais com números diferentes.
#         preferir_numero_exato = True
#         margem_override = 8 # tolerância para substituir o melhor caso
#         if preferir_numero_exato:
#             candidatos_exatos = [m for m in matches_final if m[2] == 100]
#             if candidatos_exatos:
#                 melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
#                 melhor_atual = matches_final[0]
#                 if melhor_exato[4] >= (melhor_atual[4] - margem_override):
#                     matches_final.remove(melhor_exato)
#                     matches_final.insert(0, melhor_exato)

#         # Melhor match
#         idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

#         # Monta uma lista de sugestões (top N endereços mais parecidos)
#         sugestoes_formatadas = []
#         for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
#             endereco_original = formatar_endereco(
#                 df2.loc[idx2_sug],
#                 colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
#             )
#             numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
#             sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.0f}")

#         # Salva o resultado consolidado
#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
#             "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
#             "bairro_df1": bairro1,
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])),
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "bairro_df2": df2.loc[idx2, "bairro_normalizado"],
#             "similaridade_logradouro": round(score_log, 2),
#             "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_final, 2),
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "lat": df2.loc[idx2, latitude],
#             "long": df2.loc[idx2, longitude],
#             "cd_setor": df2.loc[idx2, cd_setor]
#         })

#     return pd.DataFrame(resultados)


# ------------------------------------------------ RAPIDFUZZ COM THREAD ----------------------------------------------
# rapidfuzz.py
import os
import pandas as pd
from rapidfuzz import process, fuzz
from concurrent.futures import ThreadPoolExecutor
from comparador import formatar_endereco

# def executar_rapidfuzz(
#     df1, df2,
#     colunas_logradouro1, colunas_logradouro2,
#     col_num1=None, col_num2=None,
#     col_bairro1=None, col_bairro2=None,
#     latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#     latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#     top_n=5,
#     peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#     workers=None,
#     **kwargs
# ):
def executar_rapidfuzz(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    colunas_logradouro1_original, colunas_logradouro2_original,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    col_bairro1_original=None, col_bairro2_original=None,
    latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
    latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
    cod_unico_endereco=None,
    top_n=5, 
    peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
    workers=None,
    **kwargs
):
    """
    Compara endereços usando RapidFuzz, com paralelização por threads.
    """

    limiar_similaridade = kwargs.get("limiar_similaridade", 85)

    # define nº de threads (ex.: min(8, nº de CPUs))
    if workers is None:
        workers = min(8, (os.cpu_count() or 1))

    # helper local
    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except Exception:
            return None

    limite_candidatos = max(top_n * 5, top_n)  # ex.: 20 -> pega no máx 100

    # --------------------------
    # Função que processa UMA linha de df1
    # --------------------------
    def processar_linha(idx1):
        print(f"processando linha {idx1}")
        endereco1 = df1.at[idx1, colunas_logradouro1]
        bairro1 = df1.at[idx1, col_bairro1]
        num1_int = try_int(df1.at[idx1, col_num1]) if col_num1 else None

        # fuzzy apenas nos melhores candidatos
        matches_all = process.extract(
            endereco1,
            df2[colunas_logradouro2],
            scorer=fuzz.token_set_ratio,
            limit=limite_candidatos,
            score_cutoff=limiar_similaridade - 10  # margem
        )

        matches_final = []

        for log2_texto, score_log, idx2 in matches_all:
            num2_int = try_int(df2.at[idx2, col_num2]) if col_num2 else None
            bairro2 = df2.at[idx2, col_bairro2]

            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                score_num = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_num = None

            score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if (bairro1 or bairro2) else None

            score_final = (
                score_log * peso_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # se por algum motivo não veio ninguém acima do cutoff, aborta
        if not matches_final:
            return {
                "idx_df1": idx1,
                "endereco_df1": formatar_endereco(
                    df1.loc[idx1],
                    colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])),
                "numero_df1": df1.at[idx1, col_num1] if col_num1 else None,
                "bairro_df1": bairro1,
                "idx_df2": None,
                "cod_unico_df2": None,
                "endereco_df2": None,
                "numero_df2": None,
                "bairro_df2": None,
                "similaridade_logradouro": None,
                "similaridade_numero": None,
                "similaridade_bairro": None,
                "similaridade_final": 0.0,
                "sugestoes_topN": "",
                "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
                "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
                "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
                "latitude_resultante": None,
                "longitude_resultante": None,
                "cd_setor_resultante": None
            }

        # ordena e aplica override de número exato
        matches_final.sort(key=lambda x: x[4], reverse=True)

        preferir_numero_exato = True
        margem_override = 8
        if preferir_numero_exato:
            candidatos_exatos = [m for m in matches_final if m[2] == 100]
            if candidatos_exatos:
                melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
                melhor_atual = matches_final[0]
                if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                    matches_final.remove(melhor_exato)
                    matches_final.insert(0, melhor_exato)

        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # sugestões
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(
                df2.loc[idx2_sug],
                colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])
            )
            numero = df2.at[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.0f}")

        return {
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(
                df1.loc[idx1],
                colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])),
            "numero_df1": df1.at[idx1, col_num1] if col_num1 else None,
            "bairro_df1": bairro1,
            "idx_df2": idx2,
            "cod_unico_df2": df2.at[idx2, cod_unico_endereco],
            "endereco_df2": formatar_endereco(
                df2.loc[idx2],
                colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])),
            "numero_df2": df2.at[idx2, col_num2] if col_num2 else None,
            "bairro_df2": df2.at[idx2, col_bairro2],
            "similaridade_logradouro": round(score_log, 2),
            "similaridade_numero": round(score_num, 2) if score_num is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_final, 2),
            "sugestoes_topN": "; ".join(sugestoes_formatadas),
            "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
            "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
            "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
            "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
            "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
            "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
        }

    # --------------------------
    # Paraleliza por threads
    # --------------------------
    with ThreadPoolExecutor(max_workers=workers) as executor:
        resultados = list(executor.map(processar_linha, df1.index))

    return pd.DataFrame(resultados)





###################################################################################################################################


# # rapidfuzz.py
# import os
# import pandas as pd
# from rapidfuzz import process, fuzz
# from concurrent.futures import ThreadPoolExecutor
# from comparador import formatar_endereco


# def executar_rapidfuzz(
#     df1, df2,
#     colunas_logradouro1, colunas_logradouro2,
#     colunas_logradouro1_original, colunas_logradouro2_original,
#     col_num1=None, col_num2=None,
#     col_bairro1=None, col_bairro2=None,
#     col_bairro1_original=None, col_bairro2_original=None,
#     latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#     latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#     cod_unico_endereco=None,
#     top_n=5,  # hoje não vamos mais usar para sugestoes_topN, mas mantive por compatibilidade
#     peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#     workers=None,
#     **kwargs
# ):
#     """
#     Compara endereços usando RapidFuzz, com paralelização por threads.
#     Para cada linha de df1, retorna 1 ou mais linhas no resultado:
#     - Se houver empates na similaridade_final (empate na maior similaridade),
#       são geradas várias linhas, uma para cada idx_df2 empatado.
#     """

#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     # define nº de threads (ex.: min(8, nº de CPUs))
#     if workers is None:
#         workers = min(8, (os.cpu_count() or 1))

#     limite_candidatos = max(top_n * 5, top_n)  # ex.: 20 -> pega no máx 100

#     # --------------------------
#     # Função que processa UMA linha de df1
#     # --------------------------
#     def processar_linha(idx1):
#         # se colunas_logradouro1 for lista, você pode juntar com espaço;
#         # se já for uma coluna única, use direto.
#         endereco1 = df1.at[idx1, colunas_logradouro1]
#         bairro1 = df1.at[idx1, col_bairro1] if col_bairro1 else None
#         num1_int = df1.at[idx1, col_num1] if col_num1 else None

#         # fuzzy apenas nos melhores candidatos
#         matches_all = process.extract(
#             endereco1,
#             df2[colunas_logradouro2],
#             scorer=fuzz.token_set_ratio,
#             limit=limite_candidatos,
#             score_cutoff=limiar_similaridade - 10  # margem
#         )

#         matches_final = []

#         for log2_texto, score_log, idx2 in matches_all:
#             num2_int = df2.at[idx2, col_num2] if col_num2 else None
#             bairro2 = df2.at[idx2, col_bairro2] if col_bairro2 else None

#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 score_num = 100 if diff == 0 else max(
#                     0,
#                     100 * (1 - diff / max(num1_int, num2_int))
#                 )
#             else:
#                 score_num = None

#             score_bairro = (
#                 fuzz.token_set_ratio(bairro1, bairro2)
#                 if (bairro1 or bairro2)
#                 else None
#             )

#             score_final = (
#                 score_log * peso_logradouro +
#                 (score_num if score_num is not None else score_log) * peso_numero +
#                 (score_bairro if score_bairro is not None else score_log) * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         # --------------------------
#         # Nenhum candidato adequado
#         # --------------------------
#         if not matches_final:
#             # retorna uma LISTA com um único dict
#             return [{
#                 "idx_df1": idx1,
#                 "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])), # df1.at[idx1, colunas_logradouro1] if colunas_logradouro1 else None,
#                 "numero_df1": df1.at[idx1, col_num1] if col_num1 else None,
#                 "bairro_df1": bairro1,
#                 "idx_df2": None,
#                 "cod_unico_df2": None,
#                 "endereco_df2": None,
#                 "numero_df2": None,
#                 "bairro_df2": None,
#                 "similaridade_logradouro": None,
#                 "similaridade_numero": None,
#                 "similaridade_bairro": None,
#                 "similaridade_final": 0.0,
#                 "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#                 "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#                 "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#                 "latitude_resultante": None,
#                 "longitude_resultante": None,
#                 "cd_setor_resultante": None,
#             }]

#         # --------------------------
#         # Ordena e aplica override de número exato
#         # --------------------------
#         matches_final.sort(key=lambda x: x[4], reverse=True)

#         preferir_numero_exato = True
#         margem_override = 8

#         if preferir_numero_exato:
#             candidatos_exatos = [m for m in matches_final if m[2] == 100]
#             if candidatos_exatos:
#                 melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
#                 melhor_atual = matches_final[0]
#                 if melhor_exato[4] >= (melhor_atual[4] - margem_override):
#                     matches_final.remove(melhor_exato)
#                     matches_final.insert(0, melhor_exato)

#         # agora o melhor candidato está em matches_final[0]
#         melhor_score = matches_final[0][4]

#         # --------------------------
#         # Gera UMA LINHA para CADA CANDIDATO empatado no melhor_score
#         # --------------------------
#         linhas_resultado = []

#         for idx2, score_log, score_num, score_bairro, score_final in matches_final:
#             # só mantém empates na maior similaridade_final
#             if abs(score_final - melhor_score) > 1e-9:
#                 continue

#             linhas_resultado.append({
#                 "idx_df1": idx1,
#                 "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])), # df1.at[idx1, colunas_logradouro1] if colunas_logradouro1 else None,
#                 "numero_df1": df1.at[idx1, col_num1] if col_num1 else None,
#                 "bairro_df1": bairro1,
#                 "idx_df2": idx2,
#                 "cod_unico_df2": df2.at[idx2, cod_unico_endereco] if cod_unico_endereco else None,
#                 "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])), # df2.at[idx2, colunas_logradouro2] if colunas_logradouro2 else None,
#                 "numero_df2": df2.at[idx2, col_num2] if col_num2 else None,
#                 "bairro_df2": df2.at[idx2, col_bairro2] if col_bairro2 else None,
#                 "similaridade_logradouro": round(score_log, 2),
#                 "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#                 "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#                 "similaridade_final": round(score_final, 2),
#                 "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#                 "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#                 "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#                 "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
#                 "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
#                 "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None,
#             })

#         return linhas_resultado

#     # --------------------------
#     # Paraleliza por threads
#     # --------------------------
#     with ThreadPoolExecutor(max_workers=workers) as executor:
#         resultados_por_idx = list(executor.map(processar_linha, df1.index))

#     # resultados_por_idx é uma lista de listas -> achata
#     resultados = [linha for lista in resultados_por_idx for linha in lista]

#     return pd.DataFrame(resultados)


######################################## ULTIMO CODIGO ###########################################################

# # rapidfuzz.py
# import os
# import pandas as pd
# from rapidfuzz import process, fuzz
# from concurrent.futures import ThreadPoolExecutor
# from comparador import formatar_endereco


# def executar_rapidfuzz(
#     df1, df2,
#     colunas_logradouro1, colunas_logradouro2,
#     colunas_logradouro1_original, colunas_logradouro2_original,
#     col_num1=None, col_num2=None,
#     col_bairro1=None, col_bairro2=None,
#     col_bairro1_original=None, col_bairro2_original=None,
#     latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#     latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#     cod_unico_endereco=None,
#     top_n=5, 
#     peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#     workers=None,
#     **kwargs
# ):
#     """
#     Compara endereços usando RapidFuzz, com paralelização por threads.
#     Para cada linha de df1, retorna 1 ou mais linhas no resultado:
#     - Se houver empates na similaridade_final (empate na maior similaridade),
#       são geradas várias linhas, uma para cada idx_df2 empatado.
#     - Linhas duplicadas (mesma combinação de endereço/coords/setor) são filtradas
#       dentro de processar_linha usando um set de chaves.
#     """

#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     # define nº de threads (ex.: min(8, nº de CPUs))
#     if workers is None:
#         workers = min(8, (os.cpu_count() or 1))

#     limite_candidatos = max(top_n * 5, top_n)  # ex.: 20 -> pega no máx 100

#     # --------------------------
#     # Função que processa UMA linha de df1
#     # --------------------------
#     def processar_linha(idx1):
#         # logradouro normalizado (chave para busca)
#         endereco1_norm = df1.at[idx1, colunas_logradouro1]

#         # logradouro/bairro "originais" para exibição
#         endereco1_fmt = formatar_endereco(
#             df1.loc[idx1],
#             colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])
#         )

#         bairro1 = df1.at[idx1, col_bairro1] if col_bairro1 else None
#         num1 = df1.at[idx1, col_num1] if col_num1 else None

#         lat1 = df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None
#         lon1 = df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None
#         setor1 = df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None

#         # fuzzy apenas nos melhores candidatos
#         matches_all = process.extract(
#             endereco1_norm,
#             df2[colunas_logradouro2],
#             scorer=fuzz.token_set_ratio,
#             limit=limite_candidatos,
#             score_cutoff=limiar_similaridade - 10  # margem
#         )

#         matches_final = []

#         for log2_texto, score_log, idx2 in matches_all:
#             num2 = df2.at[idx2, col_num2] if col_num2 else None
#             bairro2 = df2.at[idx2, col_bairro2] if col_bairro2 else None

#             # similaridade do número
#             if num1 is not None and num2 is not None:
#                 try:
#                     n1 = float(num1)
#                     n2 = float(num2)
#                     diff = abs(n1 - n2)
#                     score_num = 100 if diff == 0 else max(
#                         0,
#                         100 * (1 - diff / max(n1, n2))
#                     )
#                 except Exception:
#                     score_num = None
#             else:
#                 score_num = None

#             # similaridade do bairro
#             score_bairro = (
#                 fuzz.token_set_ratio(bairro1, bairro2)
#                 if (bairro1 or bairro2)
#                 else None
#             )

#             # score final ponderado
#             score_final = (
#                 score_log * peso_logradouro +
#                 (score_num if score_num is not None else score_log) * peso_numero +
#                 (score_bairro if score_bairro is not None else score_log) * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         # --------------------------
#         # Nenhum candidato adequado
#         # --------------------------
#         if not matches_final:
#             return [{
#                 "idx_df1": idx1,
#                 "endereco_df1": endereco1_fmt,
#                 "numero_df1": num1,
#                 "bairro_df1": bairro1,
#                 "idx_df2": None,
#                 "cod_unico_df2": None,
#                 "endereco_df2": None,
#                 "numero_df2": None,
#                 "bairro_df2": None,
#                 "similaridade_logradouro": None,
#                 "similaridade_numero": None,
#                 "similaridade_bairro": None,
#                 "similaridade_final": 0.0,
#                 "latitude_verdadeira": lat1,
#                 "longitude_verdadeira": lon1,
#                 "cd_setor_verdadeiro": setor1,
#                 "latitude_resultante": None,
#                 "longitude_resultante": None,
#                 "cd_setor_resultante": None,
#             }]

#         # --------------------------
#         # Ordena e aplica override de número exato
#         # --------------------------
#         matches_final.sort(key=lambda x: x[4], reverse=True)

#         preferir_numero_exato = True
#         margem_override = 8

#         if preferir_numero_exato:
#             candidatos_exatos = [m for m in matches_final if m[2] == 100]
#             if candidatos_exatos:
#                 melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
#                 melhor_atual = matches_final[0]
#                 if melhor_exato[4] >= (melhor_atual[4] - margem_override):
#                     matches_final.remove(melhor_exato)
#                     matches_final.insert(0, melhor_exato)

#         # agora o melhor candidato está em matches_final[0]
#         melhor_score = matches_final[0][4]

#         # --------------------------
#         # Gera UMA LINHA para CADA CANDIDATO empatado no melhor_score
#         # com deduplicação via chave (set) antes de adicionar
#         # --------------------------
#         linhas_resultado = []
#         chaves_vistas = set()

#         for idx2, score_log, score_num, score_bairro, score_final in matches_final:
#             # só mantém empates na maior similaridade_final
#             if abs(score_final - melhor_score) > 1e-9:
#                 continue

#             # dados do df2 para este candidato
#             cod_unico2 = df2.at[idx2, cod_unico_endereco] if cod_unico_endereco else None
#             endereco2_fmt = formatar_endereco(
#                 df2.loc[idx2],
#                 colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])
#             )
#             num2 = df2.at[idx2, col_num2] if col_num2 else None
#             bairro2 = df2.at[idx2, col_bairro2] if col_bairro2 else None

#             lat2 = df2.at[idx2, latitude_resultante] if latitude_resultante else None
#             lon2 = df2.at[idx2, longitude_resultante] if longitude_resultante else None
#             setor2 = df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None

#             # chave para evitar duplicatas (define o que é "linha igual")
#             chave = (
#                 endereco_df1 := endereco1_fmt,
#                 numero_df1 := num1,
#                 bairro_df1 := bairro1,
#                 endereco_df2 := endereco2_fmt,
#                 numero_df2 := num2,
#                 bairro_df2 := bairro2,
#                 lat1,
#                 lon1,
#                 setor1,
#                 lat2,
#                 lon2,
#                 setor2,
#             )

#             # se já vimos essa combinação, pula
#             if chave in chaves_vistas:
#                 continue
#             chaves_vistas.add(chave)

#             linhas_resultado.append({
#                 "idx_df1": idx1,
#                 "endereco_df1": endereco_df1,
#                 "numero_df1": numero_df1,
#                 "bairro_df1": bairro_df1,
#                 "idx_df2": idx2,
#                 "cod_unico_df2": cod_unico2,
#                 "endereco_df2": endereco_df2,
#                 "numero_df2": numero_df2,
#                 "bairro_df2": bairro_df2,
#                 "similaridade_logradouro": round(score_log, 2),
#                 "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#                 "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#                 "similaridade_final": round(score_final, 2),
#                 "latitude_verdadeira": lat1,
#                 "longitude_verdadeira": lon1,
#                 "cd_setor_verdadeiro": setor1,
#                 "latitude_resultante": lat2,
#                 "longitude_resultante": lon2,
#                 "cd_setor_resultante": setor2,
#             })

#         return linhas_resultado

#     # --------------------------
#     # Paraleliza por threads
#     # --------------------------
#     with ThreadPoolExecutor(max_workers=workers) as executor:
#         resultados_por_idx = list(executor.map(processar_linha, df1.index))

#     # resultados_por_idx é uma lista de listas -> achata
#     resultados = [linha for lista in resultados_por_idx for linha in lista]

#     return pd.DataFrame(resultados)
