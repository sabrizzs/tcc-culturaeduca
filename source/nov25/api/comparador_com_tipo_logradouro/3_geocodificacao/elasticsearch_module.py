# # # elasticsearch_module.py


# import pandas as pd
# import time
# from elasticsearch import Elasticsearch, helpers
# from comparador import formatar_endereco

# ELASTICSEARCH_PW = "HO2Vv2MWa=jTr-EHSmEt"

# def recuperar_es():
#     return Elasticsearch(
#         "https://localhost:9200",
#         basic_auth=("elastic", ELASTICSEARCH_PW),
#         ca_certs="/etc/elasticsearch/certs/http_ca.crt",
#     )

# def buscar_similares_elasticsearch(
#     es,
#     endereco: str | None,
#     tipo_logradouro: str | None,
#     bairro: str | None,
#     index_name: str,
#     numero: str | int | None = None,
#     w_endereco: float = 3.0,
#     w_bairro: float = 1.0,
#     w_numero: float = 0.3,          # peso do número (bônus baixo)
#     numero_field: str = "numero",   # CAMPO NUMÉRICO (long)
#     gauss_scale: float = 2.0,       # quão “perto” conta muito (≈ metade do bônus em ±scale)
#     gauss_decay: float = 0.5,       # quanto decai na distância=scale
#     collapse_on_code: bool = True,
#     n_sugestoes: int = 5            # <<< NOVO: quantos hits retornar
# ):
#     def _wrap_num_proximity(query, numero_int):
#         # Aplica bônus por proximidade do número (gauss)
#         return {
#             "function_score": {
#                 "query": query,
#                 "functions": [
#                     {
#                         "gauss": {
#                             numero_field: {
#                                 "origin": numero_int,
#                                 "scale": gauss_scale,
#                                 "decay": gauss_decay
#                             }
#                         },
#                         "weight": w_numero
#                     }
#                 ],
#                 "score_mode": "sum",
#                 "boost_mode": "sum"
#             }
#         }

#     def _search(query, size):
#         body = {"query": query, "size": size, "track_total_hits": True}
#         if collapse_on_code:
#             body["collapse"] = {"field": "original_index"}
#         return es.search(index=index_name, **body)

#     # parse do número para inteiro (só aplica proximidade se der)
#     numero_int = None
#     if numero is not None:
#         try:
#             numero_int = int(str(numero).strip())
#         except ValueError:
#             numero_int = None  # ignora proximidade se não for inteiro

#     # --- Tentativa 1: should com boosts individuais ---
#     should = []
#     if endereco:
#         should.append({
#             "match": {
#                 "logradouro_normalizado": {
#                     "query": endereco,
#                     "fuzziness": "AUTO",
#                     "boost": w_endereco
#                 }
#             }
#         })
#         should.append({
#             "match_phrase": {
#                 "logradouro_normalizado": {
#                     "query": endereco,
#                     "slop": 2,
#                     "boost": w_endereco * 0.5
#                 }
#             }
#         })
#     if bairro:
#         should.append({
#             "match": {
#                 "bairro_normalizado": {
#                     "query": bairro,
#                     "fuzziness": "AUTO",
#                     "boost": w_bairro
#                 }
#             }
#         })

#     base_query = {"bool": {"should": should, "minimum_should_match": 1}} if should else {"match_all": {}}
#     query1 = _wrap_num_proximity(base_query, numero_int) if numero_int is not None else base_query
#     res = _search(query1, size=n_sugestoes)
#     hits = res.get("hits", {}).get("hits", [])

#     # --- Tentativa 2: cross_fields (endereco+bairro combinados)
#     if not hits and endereco and bairro:
#         combined = f"{endereco} {bairro}"
#         base2 = {
#             "multi_match": {
#                 "query": combined,
#                 "type": "cross_fields",
#                 "fields": [
#                     f"logradouro_normalizado^{w_endereco}",
#                     f"bairro_normalizado^{w_bairro}"
#                 ],
#                 "operator": "OR"
#             }
#         }
#         query2 = _wrap_num_proximity(base2, numero_int) if numero_int is not None else base2
#         res = _search(query2, size=n_sugestoes)
#         hits = res.get("hits", {}).get("hits", [])

#     # --- Tentativa 3: most_fields (mais permissivo)
#     if not hits and (endereco or bairro):
#         combined = " ".join([x for x in [endereco, bairro] if x])
#         base3 = {
#             "multi_match": {
#                 "query": combined,
#                 "type": "most_fields",
#                 "fields": [
#                     f"logradouro_normalizado^{w_endereco}",
#                     f"bairro_normalizado^{w_bairro}"
#                 ],
#             }
#         }
#         query3 = _wrap_num_proximity(base3, numero_int) if numero_int is not None else base3
#         res = _search(query3, size=n_sugestoes)
#         hits = res.get("hits", {}).get("hits", [])

#     # --- Último recurso: usa match_all mas ainda prioriza número próximo (se houver)
#     if not hits:
#         base4 = {"match_all": {}}
#         query4 = _wrap_num_proximity(base4, numero_int) if numero_int is not None else base4
#         res = _search(query4, size=n_sugestoes)
#         hits = res.get("hits", {}).get("hits", [])
#         if not hits:
#             return [(None, None, 0.0, None)]

#     # --- Normaliza todos pelo melhor score (0–100)
#     top = (hits[0].get("_score") or 1.0)
#     resultados = []
#     for h in hits[:n_sugestoes]:
#         s = h.get("_source", {})
#         score_norm = (h.get("_score", 0.0) / top) * 100.0
#         resultados.append((
#             s.get("logradouro_normalizado", ""),
#             s.get("bairro_normalizado", ""),
#             score_norm,
#             s.get("original_index"),
#         ))
#     return resultados


# def possivel_bairro_diferente(bairro1, bairro2, score_final, penalizacao=0.95):
#     """
#     Penaliza o score final se os últimos tokens (possíveis bairros) forem diferentes.
#     """
#     if bairro1 != bairro2:  # se o último token for diferente -> provável bairro diferente
#         return score_final * penalizacao
#     return score_final

# def executar_elasticsearch(df1, df2,
#                         colunas_logradouro1, colunas_logradouro2,
#                         colunas_logradouro1_original, colunas_logradouro2_original,
#                         colunas_tipo_logradouro1, colunas_tipo_logradouro2,
#                         col_num1=None, col_num2=None,
#                         col_bairro1=None, col_bairro2=None,
#                         col_bairro1_original=None, col_bairro2_original=None,
#                         latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#                         latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#                         cod_unico_endereco=None,
#                         top_n=5,
#                         peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#                         **kwargs):
#     """
#     Compara endereços usando Elasticsearch.
#     Recebe DataFrames já normalizados.
#     Retorna DataFrame padronizado com melhores matches.
#     Faz deduplicação ANTES de inserir no resultado, evitando repetir linhas
#     com os mesmos:
#       endereco_df1, endereco_df2, numero_df1, numero_df2,
#       bairro_df1, bairro_df2,
#       latitude_verdadeira, longitude_verdadeira, cd_setor_verdadeiro,
#       latitude_resultante, longitude_resultante, cd_setor_resultante.
#     """

#     index_name = "enderecos_ref"

#     resultados = []
#     # set global de chaves já vistas para evitar duplicatas
#     chaves_vistas = set()

#     # es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
#     es = recuperar_es()
#     # time.sleep(1)  # Espera para o índice estar pronto

#     df1 = df1.where(pd.notna(df1), None) # substiui as colunas NaN por None

#     for idx1, row in df1.iterrows():
#         print(f'linhas {idx1}')
#         endereco1 = row[colunas_logradouro1]
#         tipo_logradouro1 = row[colunas_tipo_logradouro1]
#         bairro1 = row[col_bairro1] if col_bairro1 else None
#         num1 = df1.loc[idx1, col_num1] if col_num1 else None

#         lat1 = df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None
#         lon1 = df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None
#         setor1 = df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None

#         similares = buscar_similares_elasticsearch(
#             es,
#             endereco1,
#             tipo_logradouro1,
#             bairro1,
#             index_name,
#             num1,
#             n_sugestoes=top_n
#         )

#         matches_final = []

#         for endereco2_texto, tipo_logradouro2, bairro2_texto, score_texto_raw, idx2 in similares:
#             if idx2 is None:
#                 continue

#             # --- SCORE DO NÚMERO (0–100)
#             num2 = df2.loc[idx2, col_num2] if col_num2 else None
#             if num1 is not None and num2 is not None:
#                 try:
#                     n1 = int(num1)
#                     n2 = int(num2)
#                     diff = abs(n1 - n2)
#                     if diff == 0:
#                         score_numero = 100.0
#                     else:
#                         score_numero = max(0.0, 100.0 * (1 - diff / max(n1, n2)))
#                 except (ValueError, TypeError):
#                     score_numero = None
#             else:
#                 score_numero = None

#             # --- SCORE DO BAIRRO (0 ou 100, simples)
#             if bairro1 and bairro2_texto:
#                 score_bairro_local = 100.0 if str(bairro1).strip() == str(bairro2_texto).strip() else 0.0
#             else:
#                 score_bairro_local = None

#             # --- SCORE FINAL: média ponderada normalizada
#             componentes = []
#             pesos = []

#             if score_texto_raw is not None:
#                 componentes.append(score_texto_raw)
#                 pesos.append(peso_logradouro)
#             if score_numero is not None:
#                 componentes.append(score_numero)
#                 pesos.append(peso_numero)
#             if score_bairro_local is not None:
#                 componentes.append(score_bairro_local)
#                 pesos.append(peso_bairro)

#             if componentes:
#                 soma_pesos = sum(pesos)
#                 score_final = sum(c * p for c, p in zip(componentes, pesos)) / soma_pesos
#             else:
#                 score_final = 0.0

#             # Penalização extra se bairro diferente
#             score_final = possivel_bairro_diferente(
#                 str(bairro1).strip() if bairro1 is not None else "",
#                 str(bairro2_texto).strip() if bairro2_texto is not None else "",
#                 score_final
#             )

#             matches_final.append((idx2, score_texto_raw, score_numero, score_bairro_local, score_final))

#         # Nenhum match razoável
#         if not matches_final:
#             endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
#             bairro_df1_fmt = (
#                 formatar_endereco(df1.loc[idx1], [col_bairro1_original])
#                 if col_bairro1_original else None
#             )

#             chave = (
#                 endereco_df1,
#                 None,              # endereco_df2
#                 num1,
#                 None,              # numero_df2
#                 bairro_df1_fmt,
#                 None,              # bairro_df2
#                 lat1,
#                 lon1,
#                 setor1,
#                 None, None, None   # latitude_resultante, longitude_resultante, cd_setor_resultante
#             )

#             if chave in chaves_vistas:
#                 continue
#             chaves_vistas.add(chave)

#             resultados.append({
#                 "idx_df1": idx1,
#                 "endereco_df1": endereco_df1,
#                 "numero_df1": num1,
#                 "bairro_df1": bairro_df1_fmt,
#                 "idx_df2": None,
#                 "endereco_df2": None,
#                 "numero_df2": None,
#                 "bairro_df2": None,
#                 "similaridade_logradouro": None,
#                 "similaridade_numero": None,
#                 "similaridade_bairro": None,
#                 "similaridade_final": None,
#                 "latitude_verdadeira": lat1,
#                 "longitude_verdadeira": lon1,
#                 "cd_setor_verdadeiro": setor1,
#                 "latitude_resultante": None,
#                 "longitude_resultante": None,
#                 "cd_setor_resultante": None
#             })
#             continue

#         # Ordena pelo score final e pega melhor match
#         matches_final.sort(key=lambda x: x[4], reverse=True)
#         idx2, score_texto, score_numero, score_bairro, melhor_score_final = matches_final[0]

#         # Monta campos do df2
#         endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
#         bairro_df1_fmt = (
#             formatar_endereco(df1.loc[idx1], [col_bairro1_original])
#             if col_bairro1_original else None
#         )

#         endereco_df2 = formatar_endereco(
#             df2.iloc[idx2],
#             colunas_logradouro2_original if colunas_logradouro2_original else colunas_logradouro2
#         )
#         num2 = df2.loc[idx2, col_num2] if col_num2 else None
#         bairro_df2_fmt = (
#             formatar_endereco(df2.loc[idx2], [col_bairro2_original])
#             if col_bairro2_original else None
#         )

#         lat2 = df2.at[idx2, latitude_resultante] if latitude_resultante else None
#         lon2 = df2.at[idx2, longitude_resultante] if longitude_resultante else None
#         setor2 = df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None

#         # chave de deduplicação
#         chave = (
#             endereco_df1,
#             endereco_df2,
#             num1,
#             num2,
#             bairro_df1_fmt,
#             bairro_df2_fmt,
#             lat1,
#             lon1,
#             setor1,
#             lat2,
#             lon2,
#             setor2,
#         )

#         if chave in chaves_vistas:
#             continue
#         chaves_vistas.add(chave)

#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": endereco_df1,
#             "numero_df1": num1,
#             "bairro_df1": bairro_df1_fmt,
#             "idx_df2": idx2,
#             "cod_unico_df2": df2.loc[idx2, cod_unico_endereco] if cod_unico_endereco else None,
#             "endereco_df2": endereco_df2,
#             "numero_df2": num2,
#             "bairro_df2": bairro_df2_fmt,
#             "similaridade_logradouro": round(score_texto, 2) if score_texto is not None else None,
#             "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
#             "latitude_verdadeira": lat1,
#             "longitude_verdadeira": lon1,
#             "cd_setor_verdadeiro": setor1,
#             "latitude_resultante": lat2,
#             "longitude_resultante": lon2,
#             "cd_setor_resultante": setor2
#         })

#     return pd.DataFrame(resultados)

# elasticsearch_module.py

import pandas as pd
import time
from elasticsearch import Elasticsearch, helpers
from comparador import formatar_endereco

ELASTICSEARCH_PW = "HO2Vv2MWa=jTr-EHSmEt"


def recuperar_es():
    return Elasticsearch(
        "https://localhost:9200",
        basic_auth=("elastic", ELASTICSEARCH_PW),
        ca_certs="/etc/elasticsearch/certs/http_ca.crt",
    )


def buscar_similares_elasticsearch(
    es,
    endereco: str | None,
    tipo_logradouro: str | None,
    bairro: str | None,
    index_name: str,
    numero: str | int | None = None,
    w_endereco: float = 3.0,
    w_tipo_logradouro: float = 2.0,   # << NOVO: peso do tipo
    w_bairro: float = 1.0,
    w_numero: float = 0.3,            # peso do número (bônus baixo)
    numero_field: str = "numero",     # CAMPO NUMÉRICO (integer/long)
    gauss_scale: float = 2.0,         # quão “perto” conta muito (≈ metade do bônus em ±scale)
    gauss_decay: float = 0.5,         # quanto decai na distância=scale
    collapse_on_code: bool = True,
    n_sugestoes: int = 5
):
    """
    Busca candidatos no índice Elasticsearch combinando:
      - logradouro_normalizado
      - tipo_logradouro_normalizado
      - bairro_normalizado
      - proximidade de número (gauss)
    """

    def _wrap_num_proximity(query, numero_int):
        # Aplica bônus por proximidade do número (gauss)
        if numero_int is None:
            return {"function_score": {"query": query}}
        return {
            "function_score": {
                "query": query,
                "functions": [
                    {
                        "gauss": {
                            numero_field: {
                                "origin": numero_int,
                                "scale": gauss_scale,
                                "decay": gauss_decay,
                            }
                        },
                        "weight": w_numero,
                    }
                ],
                "score_mode": "sum",
                "boost_mode": "sum",
            }
        }

    def _search(query, size):
        body = {"query": query, "size": size, "track_total_hits": True}
        if collapse_on_code:
            body["collapse"] = {"field": "original_index"}
        return es.search(index=index_name, **body)

    # parse do número para inteiro (só aplica proximidade se der)
    numero_int = None
    if numero is not None:
        try:
            numero_int = int(str(numero).strip())
        except ValueError:
            numero_int = None

    # --- Tentativa 1: bool should com campos separados ---
    should = []

    if endereco:
        should.append({
            "match": {
                "logradouro_normalizado": {
                    "query": endereco,
                    "fuzziness": "AUTO",
                    "boost": w_endereco,
                }
            }
        })
        should.append({
            "match_phrase": {
                "logradouro_normalizado": {
                    "query": endereco,
                    "slop": 2,
                    "boost": w_endereco * 0.5,
                }
            }
        })

    if tipo_logradouro:
        should.append({
            "match": {
                "tipo_logradouro_normalizado": {
                    "query": tipo_logradouro,
                    "boost": w_tipo_logradouro,
                }
            }
        })

    if bairro:
        should.append({
            "match": {
                "bairro_normalizado": {
                    "query": bairro,
                    "fuzziness": "AUTO",
                    "boost": w_bairro,
                }
            }
        })

    base_query = {"bool": {"should": should, "minimum_should_match": 1}} if should else {"match_all": {}}
    query1 = _wrap_num_proximity(base_query, numero_int)
    res = _search(query1, size=n_sugestoes)
    hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 2: cross_fields (endereco + tipo + bairro combinados) ---
    if not hits and (endereco or tipo_logradouro or bairro):
        combined = " ".join([x for x in [endereco, tipo_logradouro, bairro] if x])
        base2 = {
            "multi_match": {
                "query": combined,
                "type": "cross_fields",
                "fields": [
                    f"logradouro_normalizado^{w_endereco}",
                    f"tipo_logradouro_normalizado^{w_tipo_logradouro}",
                    f"bairro_normalizado^{w_bairro}",
                ],
                "operator": "OR",
            }
        }
        query2 = _wrap_num_proximity(base2, numero_int)
        res = _search(query2, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 3: most_fields (mais permissivo) ---
    if not hits and (endereco or tipo_logradouro or bairro):
        combined = " ".join([x for x in [endereco, tipo_logradouro, bairro] if x])
        base3 = {
            "multi_match": {
                "query": combined,
                "type": "most_fields",
                "fields": [
                    f"logradouro_normalizado^{w_endereco}",
                    f"tipo_logradouro_normalizado^{w_tipo_logradouro}",
                    f"bairro_normalizado^{w_bairro}",
                ],
            }
        }
        query3 = _wrap_num_proximity(base3, numero_int)
        res = _search(query3, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])

    # --- Último recurso: match_all com bônus de número ---
    if not hits:
        base4 = {"match_all": {}}
        query4 = _wrap_num_proximity(base4, numero_int)
        res = _search(query4, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            return [(None, None, None, 0.0, None)]

    # --- Normaliza todos pelo melhor score (0–100) ---
    top = (hits[0].get("_score") or 1.0)
    resultados = []
    for h in hits[:n_sugestoes]:
        s = h.get("_source", {})
        score_norm = (h.get("_score", 0.0) / top) * 100.0
        resultados.append((
            s.get("logradouro_normalizado", ""),
            s.get("tipo_logradouro_normalizado", ""),
            s.get("bairro_normalizado", ""),
            score_norm,
            s.get("original_index"),
        ))
    return resultados


def possivel_bairro_diferente(bairro1, bairro2, score_final, penalizacao=0.95):
    """
    Penaliza o score final se os bairros forem diferentes.
    """
    if bairro1 != bairro2:
        return score_final * penalizacao
    return score_final


def executar_elasticsearch(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    colunas_logradouro1_original, colunas_logradouro2_original,
    colunas_tipo_logradouro1, colunas_tipo_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    col_bairro1_original=None, col_bairro2_original=None,
    latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
    latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
    cod_unico_endereco=None,
    top_n=5,
    peso_logradouro=0.55,
    peso_tipo_logradouro=0.10,   # << NOVO
    peso_numero=0.25,
    peso_bairro=0.10,
    **kwargs
):
    """
    Compara endereços usando Elasticsearch.
    df1: base a ser geocodificada
    df2: base de referência (CNEFE)
    As colunas *_original são listas para reconstruir o endereço "bonito".
    """

    index_name = "enderecos_ref"
    resultados = []
    chaves_vistas = set()

    es = recuperar_es()

    # substitui NaN por None
    df1 = df1.where(pd.notna(df1), None)

    for idx1, row in df1.iterrows():
        print(f"linha {idx1}")

        endereco1 = row[colunas_logradouro1]
        tipo_logradouro1 = row[colunas_tipo_logradouro1]
        bairro1 = row[col_bairro1] if col_bairro1 else None
        num1 = row[col_num1] if col_num1 else None

        lat1 = row[latitude_verdadeira] if latitude_verdadeira else None
        lon1 = row[longitude_verdadeira] if longitude_verdadeira else None
        setor1 = row[cd_setor_verdadeiro] if cd_setor_verdadeiro else None

        similares = buscar_similares_elasticsearch(
            es,
            endereco1,
            tipo_logradouro1,
            bairro1,
            index_name,
            num1,
            n_sugestoes=top_n,
        )

        matches_final = []

        for endereco2_texto, tipo_logradouro2, bairro2_texto, score_texto_raw, idx2 in similares:
            if idx2 is None:
                continue

            # --- SCORE DO NÚMERO (0–100) ---
            num2 = df2.loc[idx2, col_num2] if col_num2 else None
            if num1 is not None and num2 is not None:
                try:
                    n1 = int(num1)
                    n2 = int(num2)
                    diff = abs(n1 - n2)
                    if diff == 0:
                        score_numero = 100.0
                    else:
                        score_numero = max(0.0, 100.0 * (1 - diff / max(n1, n2)))
                except (ValueError, TypeError):
                    score_numero = None
            else:
                score_numero = None

            # --- SCORE DO BAIRRO (0 ou 100) ---
            if bairro1 and bairro2_texto:
                score_bairro_local = 100.0 if str(bairro1).strip() == str(bairro2_texto).strip() else 0.0
            else:
                score_bairro_local = None

            # --- SCORE DO TIPO_LOGRADOURO (0 ou 100) ---
            if tipo_logradouro1 and tipo_logradouro2:
                score_tipo_local = 100.0 if str(tipo_logradouro1).strip() == str(tipo_logradouro2).strip() else 0.0
            else:
                score_tipo_local = None

            # --- SCORE FINAL: média ponderada normalizada ---
            componentes = []
            pesos = []

            if score_texto_raw is not None:
                componentes.append(score_texto_raw)
                pesos.append(peso_logradouro)
            if score_tipo_local is not None:
                componentes.append(score_tipo_local)
                pesos.append(peso_tipo_logradouro)
            if score_numero is not None:
                componentes.append(score_numero)
                pesos.append(peso_numero)
            if score_bairro_local is not None:
                componentes.append(score_bairro_local)
                pesos.append(peso_bairro)

            if componentes:
                soma_pesos = sum(pesos)
                score_final = sum(c * p for c, p in zip(componentes, pesos)) / soma_pesos
            else:
                score_final = 0.0

            # Penalização extra se bairro diferente
            score_final = possivel_bairro_diferente(
                str(bairro1).strip() if bairro1 is not None else "",
                str(bairro2_texto).strip() if bairro2_texto is not None else "",
                score_final,
            )

            matches_final.append((idx2, score_texto_raw, score_tipo_local, score_numero, score_bairro_local, score_final))

        # Nenhum match razoável
        if not matches_final:
            endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
            bairro_df1_fmt = (
                formatar_endereco(df1.loc[idx1], [col_bairro1_original])
                if col_bairro1_original else None
            )

            chave = (
                endereco_df1,
                None,
                num1,
                None,
                bairro_df1_fmt,
                None,
                lat1,
                lon1,
                setor1,
                None,
                None,
                None,
            )

            if chave in chaves_vistas:
                continue
            chaves_vistas.add(chave)

            resultados.append({
                "idx_df1": idx1,
                "endereco_df1": endereco_df1,
                "numero_df1": num1,
                "bairro_df1": bairro_df1_fmt,
                "idx_df2": None,
                "endereco_df2": None,
                "numero_df2": None,
                "bairro_df2": None,
                "similaridade_logradouro": None,
                "similaridade_tipo_logradouro": None,
                "similaridade_numero": None,
                "similaridade_bairro": None,
                "similaridade_final": None,
                "latitude_verdadeira": lat1,
                "longitude_verdadeira": lon1,
                "cd_setor_verdadeiro": setor1,
                "latitude_resultante": None,
                "longitude_resultante": None,
                "cd_setor_resultante": None,
            })
            continue

        # Ordena pelo score final e pega melhor match
        matches_final.sort(key=lambda x: x[5], reverse=True)
        idx2, score_texto, score_tipo, score_numero, score_bairro, melhor_score_final = matches_final[0]

        # Monta campos do df2
        endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
        bairro_df1_fmt = (
            formatar_endereco(df1.loc[idx1], [col_bairro1_original])
            if col_bairro1_original else None
        )

        endereco_df2 = formatar_endereco(
            df2.iloc[idx2],
            colunas_logradouro2_original if colunas_logradouro2_original else colunas_logradouro2,
        )
        num2 = df2.loc[idx2, col_num2] if col_num2 else None
        bairro_df2_fmt = (
            formatar_endereco(df2.loc[idx2], [col_bairro2_original])
            if col_bairro2_original else None
        )

        lat2 = df2.at[idx2, latitude_resultante] if latitude_resultante else None
        lon2 = df2.at[idx2, longitude_resultante] if longitude_resultante else None
        setor2 = df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None

        # chave de deduplicação
        chave = (
            endereco_df1,
            endereco_df2,
            num1,
            num2,
            bairro_df1_fmt,
            bairro_df2_fmt,
            lat1,
            lon1,
            setor1,
            lat2,
            lon2,
            setor2,
        )

        if chave in chaves_vistas:
            continue
        chaves_vistas.add(chave)

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": endereco_df1,
            "numero_df1": num1,
            "bairro_df1": bairro_df1_fmt,
            "idx_df2": idx2,
            "cod_unico_df2": df2.loc[idx2, cod_unico_endereco] if cod_unico_endereco else None,
            "endereco_df2": endereco_df2,
            "numero_df2": num2,
            "bairro_df2": bairro_df2_fmt,
            "similaridade_logradouro": round(score_texto, 2) if score_texto is not None else None,
            "similaridade_tipo_logradouro": round(score_tipo, 2) if score_tipo is not None else None,
            "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
            "latitude_verdadeira": lat1,
            "longitude_verdadeira": lon1,
            "cd_setor_verdadeiro": setor1,
            "latitude_resultante": lat2,
            "longitude_resultante": lon2,
            "cd_setor_resultante": setor2,
        })

    return pd.DataFrame(resultados)
