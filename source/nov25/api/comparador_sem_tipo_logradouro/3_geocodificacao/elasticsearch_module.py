# # elasticsearch_module.py


import pandas as pd
import time
from elasticsearch import Elasticsearch, helpers
from comparador import formatar_endereco

ELASTICSEARCH_PW = "HO2Vv2MWa=jTr-EHSmEt"

# def indexar_enderecos_elasticsearch(df, index_name="enderecos_ref", recreate=True, col_logradouro="logradouro_normalizado", col_bairro="bairro_normalizado", col_num="NUM_ENDERECO"):
#     es = Elasticsearch(
#         "https://localhost:9200",
#         basic_auth=("elastic", ELASTICSEARCH_PW),
#         ca_certs="/etc/elasticsearch/certs/http_ca.crt",
#     )

#     # Verifica se o Elasticsearch está acessível
#     if not es.ping():
#         raise ConnectionError("Não foi possível conectar ao Elasticsearch.")
    
#     if recreate:
#         # se existir indice ele deleta para recriar
#         if es.indices.exists(index=index_name):
#             es.indices.delete(index=index_name)

#         es.indices.create(index=index_name, mappings={
#             "properties": {
#                 "logradouro_normalizado": {"type": "text"},
#                 "bairro_normalizado": {"type": "text"},
#                 "numero": {"type": "long"},
#                 "original_index": {"type": "integer"}
#             }
#         })

#     actions = [
#         {
#             "_index": index_name,
#             "_id": i,
#             "_source": {
#                 "logradouro_normalizado": row[col_logradouro],
#                 "bairro_normalizado": row[col_bairro],
#                 "numero": int(row[col_num]),
#                 "original_index": i
#             }
#         }
#         for i, row in df.iterrows()
#     ]

#     helpers.bulk(es, actions)
#     return es

def recuperar_es():
    return Elasticsearch(
        "https://localhost:9200",
        basic_auth=("elastic", ELASTICSEARCH_PW),
        ca_certs="/etc/elasticsearch/certs/http_ca.crt",
    )


# def buscar_similares_elasticsearch(
#     es,
#     endereco: str | None,
#     bairro: str | None,
#     index_name: str,
#     numero: str | int | None = None,
#     w_endereco: float = 3.0,
#     w_bairro: float = 1.0,
#     w_numero: float = 0.3,          # peso do número (bônus baixo)
#     numero_field: str = "numero",  # CAMPO NUMÉRICO (long)
#     gauss_scale: float = 2.0,       # quão “perto” conta muito (≈ metade do bônus em ±scale)
#     gauss_decay: float = 0.5,       # quanto decai na distância=scale
#     collapse_on_code: bool = True
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

#     def _search(query, size=1):
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
#         should.append({"match": {"logradouro_normalizado": {"query": endereco, "fuzziness": "AUTO", "boost": w_endereco}}})
#         should.append({"match_phrase": {"logradouro_normalizado": {"query": endereco, "slop": 2, "boost": w_endereco * 0.5}}})
#     if bairro:
#         should.append({"match": {"bairro_normalizado": {"query": bairro, "fuzziness": "AUTO", "boost": w_bairro}}})

#     base_query = {"bool": {"should": should, "minimum_should_match": 1}} if should else {"match_all": {}}
#     query1 = _wrap_num_proximity(base_query, numero_int) if numero_int is not None else base_query
#     res = _search(query1)
#     hits = res.get("hits", {}).get("hits", [])

#     # --- Tentativa 2: cross_fields (endereco+bairro combinados)
#     if not hits and endereco and bairro:
#         combined = f"{endereco} {bairro}"
#         base2 = {
#             "multi_match": {
#                 "query": combined,
#                 "type": "cross_fields",
#                 "fields": [f"logradouro_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
#                 "operator": "OR"
#             }
#         }
#         query2 = _wrap_num_proximity(base2, numero_int) if numero_int is not None else base2
#         res = _search(query2)
#         hits = res.get("hits", {}).get("hits", [])

#     # --- Tentativa 3: most_fields (mais permissivo)
#     if not hits and (endereco or bairro):
#         combined = " ".join([x for x in [endereco, bairro] if x])
#         base3 = {
#             "multi_match": {
#                 "query": combined,
#                 "type": "most_fields",
#                 "fields": [f"logradouro_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
#             }
#         }
#         query3 = _wrap_num_proximity(base3, numero_int) if numero_int is not None else base3
#         res = _search(query3)
#         hits = res.get("hits", {}).get("hits", [])

#     # --- Último recurso: usa match_all mas ainda prioriza número próximo (se houver)
#     if not hits:
#         base4 = {"match_all": {}}
#         query4 = _wrap_num_proximity(base4, numero_int) if numero_int is not None else base4
#         res = _search(query4, size=1)
#         hits = res.get("hits", {}).get("hits", [])
#         if not hits:
#             return [(None, None, 0.0, None)]
#         h = hits[0]; s = h.get("_source", {})
#         return [(s.get("logradouro_normalizado", ""), s.get("bairro_normalizado", ""), 0.0, s.get("original_index"))]

#     # --- Normaliza pelo melhor score
#     h0 = hits[0]; s0 = h0.get("_source", {})
#     top = (h0.get("_score") or 1.0)
#     return [(
#         s0.get("logradouro_normalizado", ""),
#         s0.get("bairro_normalizado", ""),
#         (h0.get("_score", 0.0) / top) * 100.0,
#         s0.get("original_index"),
#     )]

def buscar_similares_elasticsearch(
    es,
    endereco: str | None,
    bairro: str | None,
    index_name: str,
    numero: str | int | None = None,
    w_endereco: float = 3.0,
    w_bairro: float = 1.0,
    w_numero: float = 0.3,          # peso do número (bônus baixo)
    numero_field: str = "numero",   # CAMPO NUMÉRICO (long)
    gauss_scale: float = 2.0,       # quão “perto” conta muito (≈ metade do bônus em ±scale)
    gauss_decay: float = 0.5,       # quanto decai na distância=scale
    collapse_on_code: bool = True,
    n_sugestoes: int = 5            # <<< NOVO: quantos hits retornar
):
    def _wrap_num_proximity(query, numero_int):
        # Aplica bônus por proximidade do número (gauss)
        return {
            "function_score": {
                "query": query,
                "functions": [
                    {
                        "gauss": {
                            numero_field: {
                                "origin": numero_int,
                                "scale": gauss_scale,
                                "decay": gauss_decay
                            }
                        },
                        "weight": w_numero
                    }
                ],
                "score_mode": "sum",
                "boost_mode": "sum"
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
            numero_int = None  # ignora proximidade se não for inteiro

    # --- Tentativa 1: should com boosts individuais ---
    should = []
    if endereco:
        should.append({
            "match": {
                "logradouro_normalizado": {
                    "query": endereco,
                    "fuzziness": "AUTO",
                    "boost": w_endereco
                }
            }
        })
        should.append({
            "match_phrase": {
                "logradouro_normalizado": {
                    "query": endereco,
                    "slop": 2,
                    "boost": w_endereco * 0.5
                }
            }
        })
    if bairro:
        should.append({
            "match": {
                "bairro_normalizado": {
                    "query": bairro,
                    "fuzziness": "AUTO",
                    "boost": w_bairro
                }
            }
        })

    base_query = {"bool": {"should": should, "minimum_should_match": 1}} if should else {"match_all": {}}
    query1 = _wrap_num_proximity(base_query, numero_int) if numero_int is not None else base_query
    res = _search(query1, size=n_sugestoes)
    hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 2: cross_fields (endereco+bairro combinados)
    if not hits and endereco and bairro:
        combined = f"{endereco} {bairro}"
        base2 = {
            "multi_match": {
                "query": combined,
                "type": "cross_fields",
                "fields": [
                    f"logradouro_normalizado^{w_endereco}",
                    f"bairro_normalizado^{w_bairro}"
                ],
                "operator": "OR"
            }
        }
        query2 = _wrap_num_proximity(base2, numero_int) if numero_int is not None else base2
        res = _search(query2, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 3: most_fields (mais permissivo)
    if not hits and (endereco or bairro):
        combined = " ".join([x for x in [endereco, bairro] if x])
        base3 = {
            "multi_match": {
                "query": combined,
                "type": "most_fields",
                "fields": [
                    f"logradouro_normalizado^{w_endereco}",
                    f"bairro_normalizado^{w_bairro}"
                ],
            }
        }
        query3 = _wrap_num_proximity(base3, numero_int) if numero_int is not None else base3
        res = _search(query3, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])

    # --- Último recurso: usa match_all mas ainda prioriza número próximo (se houver)
    if not hits:
        base4 = {"match_all": {}}
        query4 = _wrap_num_proximity(base4, numero_int) if numero_int is not None else base4
        res = _search(query4, size=n_sugestoes)
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            return [(None, None, 0.0, None)]

    # --- Normaliza todos pelo melhor score (0–100)
    top = (hits[0].get("_score") or 1.0)
    resultados = []
    for h in hits[:n_sugestoes]:
        s = h.get("_source", {})
        # score_norm = (h.get("_score", 0.0) / top) * 100.0
        score_norm = h.get("_score", 0.0) / top
        resultados.append((
            s.get("logradouro_normalizado", ""),
            s.get("bairro_normalizado", ""),
            score_norm,
            s.get("original_index"),
        ))
    return resultados


def possivel_bairro_diferente(bairro1, bairro2, score_final, penalizacao=0.95):
    """
    Penaliza o score final se os últimos tokens (possíveis bairros) forem diferentes.
    """
    if bairro1 != bairro2:  # se o último token for diferente -> provável bairro diferente
        return score_final * penalizacao
    return score_final



# def executar_elasticsearch(df1, df2,
#                         colunas_logradouro1, colunas_logradouro2,
#                         colunas_logradouro1_original, colunas_logradouro2_original,
#                         col_num1=None, col_num2=None,
#                         col_bairro1=None, col_bairro2=None,
#                         col_bairro1_original=None, col_bairro2_original=None,
#                         latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#                         latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#                         cod_unico_endereco=None,
#                         top_n=5,
#                         peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#                         **kwargs):
#     # limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     """
#     Compara endereços usando Elasticsearch.
#     Recebe DataFrames já normalizados.
#     Retorna DataFrame padronizado com melhores matches e top N sugestões.
#     """
#     index_name = "enderecos_ref"

#     resultados = []
        
#     es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
#     time.sleep(1)  # Espera para o índice estar pronto

#     for idx1, row in df1.iterrows():
#         endereco1 = row[colunas_logradouro1]
#         bairro1 = row[col_bairro1] if col_bairro1 else None

#         num1 = df1.loc[idx1, col_num1] if col_num1 else None

#         similares = buscar_similares_elasticsearch(
#             es,
#             endereco1,
#             bairro1,
#             index_name,
#             num1,
#             n_sugestoes=top_n
#         )

#         matches_final = []

#         for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
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
#                         # Similaridade baseada na proximidade dos números
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

#             # Penalização extra se bairro diferente (mantive sua lógica)
#             score_final = possivel_bairro_diferente(
#                 str(bairro1).strip() if bairro1 is not None else "",
#                 str(bairro2_texto).strip() if bairro2_texto is not None else "",
#                 score_final
#             )

#             matches_final.append((idx2, score_texto_raw, score_numero, score_bairro_local, score_final))

#         if not matches_final:
#             # nenhum match razoável
#             resultados.append({
#                 "idx_df1": idx1,
#                 "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original),
#                 "numero_df1": num1,
#                 "bairro_df1": formatar_endereco(df1.loc[idx1], [col_bairro1_original]) if col_bairro1_original else None,
#                 "idx_df2": None,
#                 "endereco_df2": None,
#                 "numero_df2": None,
#                 "bairro_df2": None,
#                 "similaridade_logradouro": None,
#                 "similaridade_numero": None,
#                 "similaridade_bairro": None,
#                 "similaridade_final": None,
#                 "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#                 "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#                 "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#                 "latitude_resultante": None,
#                 "longitude_resultante": None,
#                 "cd_setor_resultante": None
#             })

#             continue

#         # Ordena pelo score final
#         matches_final.sort(key=lambda x: x[4], reverse=True)

#         # Melhor match
#         idx2, score_texto, score_numero, score_bairro, melhor_score_final = matches_final[0]

#         # Sugestões top N pelo score final
#         # sugestoes_formatadas = []
#         # for idx2_sug, score_texto_sug, score_numero_sug, score_bairro_sug, score_final_sug in matches_final[:top_n]:
#         #     endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2)
#         #     numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
#         #     score_final_str = f"{score_final_sug:.0f}" if score_final_sug is not None else "N/A"
#         #     sugestoes_formatadas.append(
#         #         f"{endereco_original} {numero} | Score Final: {score_final_str}"
#         #     )

#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original),
#             "numero_df1": num1,
#             "bairro_df1": formatar_endereco(df1.loc[idx1], [col_bairro1_original]) if col_bairro1_original else None,
#             "idx_df2": idx2,
#             "cod_unico_df2": df2.loc[idx2, cod_unico_endereco] if cod_unico_endereco else None,
#             "endereco_df2": formatar_endereco(df2.iloc[idx2], colunas_logradouro2_original if colunas_logradouro2_original else colunas_logradouro2),
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "bairro_df2": formatar_endereco(df2.loc[idx2], [col_bairro2_original]) if col_bairro2_original else None,
#             "similaridade_logradouro": round(score_texto, 2) if score_texto is not None else None,
#             "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
#             #"sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#             "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#             "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#             "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
#             "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
#             "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
#         })

#     return pd.DataFrame(resultados)

def executar_elasticsearch(df1, df2,
                        colunas_logradouro1, colunas_logradouro2,
                        colunas_logradouro1_original, colunas_logradouro2_original,
                        colunas_complemento1=None, colunas_complemento2=None,
                        col_num1=None, col_num2=None,
                        col_bairro1=None, col_bairro2=None,
                        col_bairro1_original=None, col_bairro2_original=None,
                        latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
                        latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
                        cod_unico_endereco=None,
                        top_n=5,
                        peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
                        **kwargs):
    """
    Compara endereços usando Elasticsearch.
    Recebe DataFrames já normalizados.
    Retorna DataFrame padronizado com melhores matches.
    Faz deduplicação ANTES de inserir no resultado, evitando repetir linhas
    com os mesmos:
      endereco_df1, endereco_df2, numero_df1, numero_df2,
      bairro_df1, bairro_df2,
      latitude_verdadeira, longitude_verdadeira, cd_setor_verdadeiro,
      latitude_resultante, longitude_resultante, cd_setor_resultante.
    """

    index_name = "enderecos_ref"

    resultados = []
    # set global de chaves já vistas para evitar duplicatas
    chaves_vistas = set()

    # es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
    es = recuperar_es()
    # time.sleep(1)  # Espera para o índice estar pronto

    df1 = df1.where(pd.notna(df1), None) # substiui as colunas NaN por None

    for idx1, row in df1.iterrows():
        print(f'linhas {idx1}')
        endereco1 = row[colunas_logradouro1]
        bairro1 = row[col_bairro1] if col_bairro1 else None
        num1 = df1.loc[idx1, col_num1] if col_num1 else None

        lat1 = df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None
        lon1 = df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None
        setor1 = df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None

        similares = buscar_similares_elasticsearch(
            es,
            endereco1,
            bairro1,
            index_name,
            num1,
            n_sugestoes=top_n
        )

        matches_final = []

        for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
            if idx2 is None:
                continue

            # --- SCORE DO NÚMERO (0–100)
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

            # --- SCORE DO BAIRRO (0 ou 100, simples)
            if bairro1 and bairro2_texto:
                score_bairro_local = 100.0 if str(bairro1).strip() == str(bairro2_texto).strip() else 0.0
            else:
                score_bairro_local = None

            # --- SCORE FINAL: média ponderada normalizada
            componentes = []
            pesos = []

            if score_texto_raw is not None:
                componentes.append(score_texto_raw)
                pesos.append(peso_logradouro)
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
                score_final
            )

            matches_final.append((idx2, score_texto_raw, score_numero, score_bairro_local, score_final))

        # Nenhum match razoável
        if not matches_final:
            endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
            bairro_df1_fmt = (
                formatar_endereco(df1.loc[idx1], [col_bairro1_original])
                if col_bairro1_original else None
            )
            complemento_df1 = formatar_endereco(df1.loc[idx1], colunas_complemento1)

            chave = (
                endereco_df1,
                None,              # endereco_df2
                num1,
                None,              # numero_df2
                complemento_df1,
                None,              # complemento_df2
                bairro_df1_fmt,
                None,              # bairro_df2
                lat1,
                lon1,
                setor1,
                None, None, None   # latitude_resultante, longitude_resultante, cd_setor_resultante
            )

            if chave in chaves_vistas:
                continue
            chaves_vistas.add(chave)

            resultados.append({
                "idx_df1": idx1,
                "endereco_df1": endereco_df1,
                "numero_df1": num1,
                "complemento_df1": complemento_df1,
                "bairro_df1": bairro_df1_fmt,
                "idx_df2": None,
                "endereco_df2": None,
                "numero_df2": None,
                "complemento_df2": None,
                "bairro_df2": None,
                "similaridade_logradouro": None,
                "similaridade_numero": None,
                "similaridade_bairro": None,
                "similaridade_final": None,
                "latitude_verdadeira": lat1,
                "longitude_verdadeira": lon1,
                "cd_setor_verdadeiro": setor1,
                "latitude_resultante": None,
                "longitude_resultante": None,
                "cd_setor_resultante": None
            })
            continue

        # Ordena pelo score final e pega melhor match
        matches_final.sort(key=lambda x: x[4], reverse=True)
        idx2, score_texto, score_numero, score_bairro, melhor_score_final = matches_final[0]

        # Monta campos do df2
        endereco_df1 = formatar_endereco(df1.loc[idx1], colunas_logradouro1_original)
        bairro_df1_fmt = (
            formatar_endereco(df1.loc[idx1], [col_bairro1_original])
            if col_bairro1_original else None
        )
        complemento_df1 = formatar_endereco(df1.loc[idx1], colunas_complemento1)

        endereco_df2 = formatar_endereco(
            df2.iloc[idx2],
            colunas_logradouro2_original if colunas_logradouro2_original else colunas_logradouro2
        )
        num2 = df2.loc[idx2, col_num2] if col_num2 else None
        bairro_df2_fmt = (
            formatar_endereco(df2.loc[idx2], [col_bairro2_original])
            if col_bairro2_original else None
        )
        complemento_df2 = formatar_endereco(df2.loc[idx2], colunas_complemento2)

        lat2 = df2.at[idx2, latitude_resultante] if latitude_resultante else None
        lon2 = df2.at[idx2, longitude_resultante] if longitude_resultante else None
        setor2 = df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None

        # chave de deduplicação
        chave = (
            endereco_df1,
            endereco_df2,
            num1,
            num2,
            complemento_df1,
            complemento_df2,
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
            "complemento_df1": complemento_df1,
            "bairro_df1": bairro_df1_fmt,
            "idx_df2": idx2,
            "cod_unico_df2": df2.loc[idx2, cod_unico_endereco] if cod_unico_endereco else None,
            "endereco_df2": endereco_df2,
            "numero_df2": num2,
            "complemento_df2": complemento_df2,
            "bairro_df2": bairro_df2_fmt,
            "similaridade_logradouro": round(score_texto, 2) if score_texto is not None else None,
            "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
            "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
            "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
            "latitude_verdadeira": lat1,
            "longitude_verdadeira": lon1,
            "cd_setor_verdadeiro": setor1,
            "latitude_resultante": lat2,
            "longitude_resultante": lon2,
            "cd_setor_resultante": setor2
        })

    return pd.DataFrame(resultados)




###############################################ultimo utilizado###################################################

# def executar_elasticsearch(df1, df2,
#                         colunas_logradouro1, colunas_logradouro2,
#                         colunas_logradouro1_original, colunas_logradouro2_original,
#                         col_num1=None, col_num2=None,
#                         col_bairro1=None, col_bairro2=None,
#                         col_bairro1_original=None, col_bairro2_original=None,
#                         latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
#                         latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
#                         cod_unico_endereco=None,
#                         top_n=5,
#                         peso_logradouro=0.65, peso_numero=0.3, peso_bairro=0.05,
#                         **kwargs):
#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     """
#     Compara endereços usando Elasticsearch.
#     Recebe DataFrames já carregados, mas aplica normalização de logradouro e bairro.
#     Retorna DataFrame padronizado com melhores matches e top N sugestões.
#     """
#     index_name = "enderecos_ref"
#     # df1 = df1.copy()
#     # df2 = df2.copy()

#     # # Normalização de logradouro e bairro
#     # df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
#     # df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

#     # df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
#     # df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

#     resultados = []

#     def try_int(n):
#         if pd.isna(n):
#             return None
#         try:
#             return int(float(n))
#         except:
#             return None
        
#     es = indexar_enderecos_elasticsearch(df2, index_name=index_name)
#     time.sleep(1)  # Espera para o índice estar pronto

#     resultados = []
    
#     for idx1, row in df1.iterrows():
#         endereco1 = row["logradouro_normalizado"]
#         bairro1 = row["bairro_normalizado"]

#         num1 = df1.loc[idx1, col_num1] if col_num1 else None
#         num1_int = try_int(num1)

#         similares = buscar_similares_elasticsearch(es, endereco1, bairro1, index_name, num1_int)

#         matches_final = []
        
#         for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
#             num2 = df2.loc[idx2, col_num2] if col_num2 else None
#             num2_int = try_int(num2)
#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 if diff == 0:
#                     score_numero = 100
#                 else:
#                     # Similaridade baseada em quão próximos estão os numeros dos endereços
#                     score_numero = max(0, 100 * (1 - diff / max(num1_int, num2_int)))
#             else:
#                 score_numero = None
#             if score_numero is None:
#                 score_final = score_texto_raw
#             else:
#                 score_final = score_texto_raw * peso_logradouro + score_numero * peso_numero
#             score_final = possivel_bairro_diferente(bairro1, bairro2_texto, score_final)
#             matches_final.append((idx2, score_texto_raw, score_numero, score_final))
#         # Ordena pelo score final
#         matches_final.sort(key=lambda x: x[3], reverse=True)
#         # Melhor match
#         idx2, score_texto, score_numero, melhor_score_final = matches_final[0]
#         # Sugestões top N pelo score final
#         sugestoes_formatadas = []
#         for idx2_sug, score_texto_sug, score_numero_sug, score_final_sug in matches_final[:top_n]:
#             endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2)
            
#             # Adiciona o número
#             numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            
#             score_final_str = f"{score_final_sug:.0f}" if score_final_sug is not None else "N/A"
#             sugestoes_formatadas.append(
#                 f"{endereco_original} {numero} | Score Final: {score_final_str}"
#             )
        
#         # Armazena o resultado no DataFrame final
#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1),
#             "bairro_df1": formatar_endereco(df1.loc[idx1], [col_bairro1]),
#             "numero_df1": num1_int,
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.iloc[idx2], colunas_logradouro2),
#             "bairro_df2": formatar_endereco(df2.loc[idx2], [col_bairro2]),
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "similaridade_texto": round(score_texto, 2),
#             "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
#             "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
#             "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
#             "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
#             "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
#             "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
#             "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
#         })


#     return pd.DataFrame(resultados)

##################################################################################################

# from joblib import Parallel, delayed
# import pandas as pd
# import time

# from comparador import montar_logradouro, normalize_bairro, formatar_endereco
# from elasticsearch import Elasticsearch

# def try_int(n):
#     if pd.isna(n):
#         return None
#     try:
#         return int(float(n))
#     except:
#         return None
    
# def executar_elasticsearch(
#     df1: pd.DataFrame,
#     df2: pd.DataFrame,
#     colunas_logradouro1,
#     colunas_logradouro2,
#     col_num1=None,
#     col_num2=None,
#     col_bairro1=None,
#     col_bairro2=None,
#     latitude=None,
#     longitude=None,
#     cd_setor=None,
#     top_n: int = 5,
#     peso_logradouro: float = 0.65,
#     peso_numero: float = 0.3,
#     peso_bairro: float = 0.05,
#     index_name: str = "enderecos_ref",
#     recreate_index: bool = True,
#     n_jobs: int = 8,   # <<< paralelismo Python aqui
#     **kwargs,
# ) -> pd.DataFrame:

#     limiar_similaridade = kwargs.get("limiar_similaridade", 85)

#     df1 = df1.copy()
#     df2 = df2.copy()

#     # Normalização de logradouro e bairro
#     df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
#     df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

#     df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
#     df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

#     # Indexa df2 (referência) UMA VEZ só
#     es = indexar_enderecos_elasticsearch(df2, index_name=index_name, recreate=recreate_index, col_logradouro="logradouro_normalizado", col_bairro="bairro_normalizado", col_num=col_num2)
#     time.sleep(1)  # pequena espera pro índice estabilizar

#     # -----------------------------
#     # Função que processa UMA linha de df1
#     # -----------------------------
#     def processar_linha(idx1, row1):
#         endereco1 = row1["logradouro_normalizado"]
#         bairro1 = row1["bairro_normalizado"]

#         num1 = row1[col_num1] if col_num1 else None
#         num1_int = try_int(num1)

#         similares = buscar_similares_elasticsearch(
#             es,
#             endereco=endereco1,
#             bairro=bairro1,
#             index_name=index_name,
#             numero=num1_int
#         )

#         if not similares:
#             return None

#         matches_final = []

#         for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
#             if idx2 is None:
#                 continue

#             num2 = df2.loc[idx2, col_num2] if col_num2 else None
#             num2_int = try_int(num2)

#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 if diff == 0:
#                     score_numero = 100
#                 else:
#                     score_numero = max(0, 100 * (1 - diff / max(num1_int, num2_int)))
#             else:
#                 score_numero = None

#             if score_numero is None:
#                 score_final = score_texto_raw
#             else:
#                 score_final = score_texto_raw * peso_logradouro + score_numero * peso_numero

#             score_final = possivel_bairro_diferente(bairro1, bairro2_texto, score_final)

#             matches_final.append((idx2, score_texto_raw, score_numero, score_final))

#         if not matches_final:
#             return None

#         matches_final.sort(key=lambda x: x[3], reverse=True)
#         idx2, score_texto, score_numero, melhor_score_final = matches_final[0]

#         # se quiser aplicar filtro pelo limiar:
#         # if melhor_score_final < limiar_similaridade:
#         #     return None

#         # Monta sugestões
#         sugestoes = []
#         for idx2_sug, score_t_sug, score_n_sug, score_f_sug in matches_final[:top_n]:
#             end_orig = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2)
#             num2_sug = df2.loc[idx2_sug, col_num2] if col_num2 else ""
#             sugestoes.append(f"{end_orig} {num2_sug} | Score Final: {score_f_sug:.0f}")

#         return {
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(row1, colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
#             "bairro_df1": row1[col_bairro1] if col_bairro1 else None,
#             "numero_df1": num1_int,
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])),
#             "bairro_df2": df2.loc[idx2, col_bairro2] if col_bairro2 else None,
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "similaridade_texto": round(score_texto, 2),
#             "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
#             "similaridade_final": round(melhor_score_final, 2),
#             "sugestoes_topN": "; ".join(sugestoes),
#             "lat": df2.at[idx2, latitude] if latitude else None,
#             "long": df2.at[idx2, longitude] if longitude else None,
#             "cd_setor": df2.at[idx2, cd_setor] if cd_setor else None,
#         }

#     # -----------------------------
#     # Paralelização SÓ no lado Python
#     # -----------------------------
#     resultados = Parallel(n_jobs=n_jobs, prefer="threads")(
#         delayed(processar_linha)(idx1, row1)
#         for idx1, row1 in df1.iterrows()
#     )

#     # Remove os None
#     resultados = [r for r in resultados if r is not None]

#     return pd.DataFrame(resultados)
