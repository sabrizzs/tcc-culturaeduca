
# # ------------------------------------------------ RAPIDFUZZ COM THREAD ----------------------------------------------
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
#     col_tipo_logradouro1, col_tipo_logradouro2,
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
#     """

#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     # define nº de threads (ex.: min(8, nº de CPUs))
#     if workers is None:
#         workers = min(8, (os.cpu_count() or 1))

#     # helper local
#     def try_int(n):
#         if pd.isna(n):
#             return None
#         try:
#             return int(float(n))
#         except Exception:
#             return None

#     limite_candidatos = max(top_n * 5, top_n)  # ex.: 20 -> pega no máx 100

#     # --------------------------
#     # Função que processa UMA linha de df1
#     # --------------------------
#     def processar_linha(idx1):
#         endereco1 = df1.at[idx1, colunas_logradouro1]
#         tipo_logradouro1 = df1.at[idx1, col_tipo_logradouro1]
#         bairro1 = df1.at[idx1, col_bairro1]
#         num1_int = try_int(df1.at[idx1, col_num1]) if col_num1 else None

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
#             num2_int = try_int(df2.at[idx2, col_num2]) if col_num2 else None
#             bairro2 = df2.at[idx2, col_bairro2]

#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 score_num = 100 if diff == 0 else max(0, 100 * (1 - diff / max(num1_int, num2_int)))
#             else:
#                 score_num = None

#             score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if (bairro1 or bairro2) else None

#             score_final = (
#                 score_log * peso_logradouro +
#                 (score_num if score_num is not None else score_log) * peso_numero +
#                 (score_bairro if score_bairro is not None else score_log) * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         # se por algum motivo não veio ninguém acima do cutoff, aborta
#         if not matches_final:
#             return {
#                 "idx_df1": idx1,
#                 "endereco_df1": formatar_endereco(
#                     df1.loc[idx1],
#                     colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])),
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
#                 "sugestoes_topN": "",
#                 "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#                 "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#                 "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#                 "latitude_resultante": None,
#                 "longitude_resultante": None,
#                 "cd_setor_resultante": None
#             }

#         # ordena e aplica override de número exato
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

#         idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

#         # sugestões
#         sugestoes_formatadas = []
#         for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
#             endereco_original = formatar_endereco(
#                 df2.loc[idx2_sug],
#                 colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])
#             )
#             numero = df2.at[idx2_sug, col_num2] if col_num2 else ""
#             sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.0f}")

#         return {
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(
#                 df1.loc[idx1],
#                 colunas_logradouro1_original + ([col_bairro1_original] if col_bairro1_original else [])),
#             "numero_df1": df1.at[idx1, col_num1] if col_num1 else None,
#             "bairro_df1": bairro1,
#             "idx_df2": idx2,
#             "cod_unico_df2": df2.at[idx2, cod_unico_endereco],
#             "endereco_df2": formatar_endereco(
#                 df2.loc[idx2],
#                 colunas_logradouro2_original + ([col_bairro2_original] if col_bairro2_original else [])),
#             "numero_df2": df2.at[idx2, col_num2] if col_num2 else None,
#             "bairro_df2": df2.at[idx2, col_bairro2],
#             "similaridade_logradouro": round(score_log, 2),
#             "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_final, 2),
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#             "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#             "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#             "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
#             "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
#             "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
#         }

#     # --------------------------
#     # Paraleliza por threads
#     # --------------------------
#     with ThreadPoolExecutor(max_workers=workers) as executor:
#         resultados = list(executor.map(processar_linha, df1.index))

#     return pd.DataFrame(resultados)

import os
import pandas as pd
from rapidfuzz import process, fuzz
from concurrent.futures import ThreadPoolExecutor
from comparador import formatar_endereco


def executar_rapidfuzz(
    df1, df2,
    col_logradouro1, col_logradouro2,
    colunas_logradouro1_original, colunas_logradouro2_original,
    col_tipo_logradouro1, col_tipo_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    col_bairro1_original=None, col_bairro2_original=None,
    latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
    latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
    cod_unico_endereco=None,
    top_n=5,
    peso_logradouro=0.55,
    peso_tipo_logradouro=0.10,     # << NOVO
    peso_numero=0.25,
    peso_bairro=0.10,
    workers=None,
    **kwargs
):
    """
    Compara endereços usando RapidFuzz, agora incluindo tipo de logradouro.
    """

    limiar_similaridade = kwargs.get("limiar_similaridade", 85)

    if workers is None:
        workers = min(8, (os.cpu_count() or 1))

    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except Exception:
            return None

    limite_candidatos = max(top_n * 5, top_n)

    # ---------------------------------------------------------------------
    # PROCESSAR UMA LINHA
    # ---------------------------------------------------------------------
    def processar_linha(idx1):
        print(f"processando linha {idx1}")
        endereco1 = df1.at[idx1, col_logradouro1]
        tipo1 = df1.at[idx1, col_tipo_logradouro1]
        bairro1 = df1.at[idx1, col_bairro1]
        num1_int = try_int(df1.at[idx1, col_num1]) if col_num1 else None

        # fuzzy inicial
        matches_all = process.extract(
            endereco1,
            df2[col_logradouro2],
            scorer=fuzz.token_set_ratio,
            limit=limite_candidatos,
            score_cutoff=limiar_similaridade - 10
        )

        matches_final = []

        for log2_texto, score_log, idx2 in matches_all:
            tipo2 = df2.at[idx2, col_tipo_logradouro2]
            bairro2 = df2.at[idx2, col_bairro2]
            num2_int = try_int(df2.at[idx2, col_num2]) if col_num2 else None

            # Similaridade tipo logradouro
            score_tipo = fuzz.ratio(str(tipo1), str(tipo2)) if (tipo1 or tipo2) else None

            # Similaridade número
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                score_num = 100 if diff == 0 else max(
                    0, 100 * (1 - diff / max(num1_int, num2_int))
                )
            else:
                score_num = None

            # Similaridade bairro
            score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if (bairro1 or bairro2) else None

            # Score final ponderado
            score_final = (
                score_log * peso_logradouro +
                (score_tipo if score_tipo is not None else score_log) * peso_tipo_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches_final.append((idx2, score_log, score_tipo, score_num, score_bairro, score_final))

        if not matches_final:
            return {
                "idx_df1": idx1,
                "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original),
                "numero_df1": df1.at[idx1, col_num1],
                "bairro_df1": bairro1,
                "idx_df2": None,
                "cod_unico_df2": None,
                "endereco_df2": None,
                "numero_df2": None,
                "bairro_df2": None,
                "similaridade_logradouro": None,
                "similaridade_tipo": None,
                "similaridade_numero": None,
                "similaridade_bairro": None,
                "similaridade_final": 0.0,
                "sugestoes_topN": "",
            }

        matches_final.sort(key=lambda x: x[5], reverse=True)
        idx2, score_log, score_tipo, score_num, score_bairro, melhor_final = matches_final[0]

        # Sugestões
        sugestoes = []
        for sug_idx2, s_log, s_tipo, s_num, s_bai, s_final in matches_final[:top_n]:
            endereco_sug = formatar_endereco(
                df2.loc[sug_idx2],
                colunas_logradouro2_original
            )
            sugestoes.append(f"{endereco_sug} | Score Final: {s_final:.0f}")

        return {
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original),
            "numero_df1": df1.at[idx1, col_num1],
            "bairro_df1": bairro1,
            "idx_df2": idx2,
            "cod_unico_df2": df2.at[idx2, cod_unico_endereco],
            "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2_original),
            "numero_df2": df2.at[idx2, col_num2],
            "bairro_df2": df2.at[idx2, col_bairro2],
            "similaridade_logradouro": round(score_log, 2),
            "similaridade_tipo": round(score_tipo, 2) if score_tipo is not None else None,
            "similaridade_numero": round(score_num, 2) if score_num is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_final, 2),
            "sugestoes_topN": "; ".join(sugestoes),

            "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
            "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
            "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,

            "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
            "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
            "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None,
        }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        resultados = list(executor.map(processar_linha, df1.index))

    return pd.DataFrame(resultados)
