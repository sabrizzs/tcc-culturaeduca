# # elasticsearch_module.py


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
    bairro: str | None,
    index_name: str,
    numero: str | int | None = None,
    w_endereco: float = 3.0,
    w_bairro: float = 1.0,
    w_numero: float = 0.3,          # peso do número (bônus baixo)
    numero_field: str = "numero",  # CAMPO NUMÉRICO (long)
    gauss_scale: float = 2.0,       # quão “perto” conta muito (≈ metade do bônus em ±scale)
    gauss_decay: float = 0.5,       # quanto decai na distância=scale
    collapse_on_code: bool = True,
    max_hits: int = 50,             # NOVO: quantos candidatos trazer do ES
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

    def _search(query, size=None):
        # size padrão = max_hits
        body = {
            "query": query,
            "size": size or max_hits,
            "track_total_hits": True
        }
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
    res = _search(query1)
    hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 2: cross_fields (endereco+bairro combinados)
    if not hits and endereco and bairro:
        combined = f"{endereco} {bairro}"
        base2 = {
            "multi_match": {
                "query": combined,
                "type": "cross_fields",
                "fields": [f"logradouro_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
                "operator": "OR"
            }
        }
        query2 = _wrap_num_proximity(base2, numero_int) if numero_int is not None else base2
        res = _search(query2)
        hits = res.get("hits", {}).get("hits", [])

    # --- Tentativa 3: most_fields (mais permissivo)
    if not hits and (endereco or bairro):
        combined = " ".join([x for x in [endereco, bairro] if x])
        base3 = {
            "multi_match": {
                "query": combined,
                "type": "most_fields",
                "fields": [f"logradouro_normalizado^{w_endereco}", f"bairro_normalizado^{w_bairro}"],
            }
        }
        query3 = _wrap_num_proximity(base3, numero_int) if numero_int is not None else base3
        res = _search(query3)
        hits = res.get("hits", {}).get("hits", [])

    # --- Último recurso: usa match_all mas ainda prioriza número próximo (se houver)
    if not hits:
        base4 = {"match_all": {}}
        query4 = _wrap_num_proximity(base4, numero_int) if numero_int is not None else base4
        res = _search(query4, size=1)
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            # nada encontrado mesmo
            return [(None, None, 0.0, None)]
        h = hits[0]
        s = h.get("_source", {})
        return [(
            s.get("logradouro_normalizado", ""),
            s.get("bairro_normalizado", ""),
            0.0,
            s.get("original_index"),
        )]

    # --- Normaliza pelo melhor score e devolve TODOS os hits ---
    top_score = hits[0].get("_score") or 1.0
    similares = []
    for h in hits:
        s = h.get("_source", {})
        raw = h.get("_score", 0.0)
        score_pct = (raw / top_score) * 100.0 if top_score > 0 else 0.0
        similares.append((
            s.get("logradouro_normalizado", ""),
            s.get("bairro_normalizado", ""),
            score_pct,
            s.get("original_index"),
        ))
    return similares

from rapidfuzz import fuzz

def executar_elasticsearch(
    df1, df2,
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
    workers=None,
    **kwargs
):
    """
    Compara endereços usando Elasticsearch.
    Recebe DataFrames já carregados, mas aplica normalização de logradouro e bairro.
    Retorna DataFrame padronizado com melhores matches e top N sugestões.
    """
    index_name = "enderecos_ref"

    es = recuperar_es()

    def try_int(n):
        if pd.isna(n):
            return None
        try:
            return int(float(n))
        except:
            return None

    resultados = []
    
    for idx1, row in df1.iterrows():
        endereco1 = row[colunas_logradouro1]
        bairro1 = row[col_bairro1]

        num1 = df1.loc[idx1, col_num1] if col_num1 else None
        num1_int = try_int(num1)

        # Agora buscar_similares_elasticsearch devolve vários candidatos
        similares = buscar_similares_elasticsearch(
            es,
            endereco1,
            bairro1,
            index_name,
            num1_int,
            max_hits=max(top_n * 3, 20)  # traz mais candidatos para poder ter empate
        )

        matches_final = []
        
        for endereco2_texto, bairro2_texto, score_texto_raw, idx2 in similares:
            if idx2 is None:
                continue

            num2 = df2.loc[idx2, col_num2] if col_num2 else None
            num2_int = try_int(num2)

            # Similaridade do número (baseada na proximidade)
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_numero = 100.0
                else:
                    score_numero = max(0.0, 100.0 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_numero = None

            # similaridade do bairro
            score_bairro = (
                fuzz.token_set_ratio(bairro1, bairro2_texto)
                if (bairro1 or bairro2_texto)
                else None
            )

            # Combinação de scores
            if score_numero is None:
                score_final = score_texto_raw # leva em consideração o bairro e o logradouro
            else:
                score_final = score_texto_raw * peso_logradouro + score_numero * peso_numero

            matches_final.append((idx2, score_texto_raw, score_numero, score_final, score_bairro))

        # Se nada foi encontrado, apenas pula ou cria linha vazia
        if not matches_final:
            continue

        # Ordena pelo score final (decrescente)
        matches_final.sort(key=lambda x: x[3] if x[3] is not None else -1, reverse=True)

        # Melhor score_final
        melhor_score_final = matches_final[0][3]
        melhor_score_final_round = round(melhor_score_final, 2) if melhor_score_final is not None else None

        # TODOS os empatados: mesmo score_final ARREDONDADO
        melhores_matches = [
            (idx2, score_texto, score_numero, score_final, score_bairro)
            for (idx2, score_texto, score_numero, score_final, score_bairro) in matches_final
            if (score_final is not None and round(score_final, 2) == melhor_score_final_round)
        ]

        # Sugestões top N pelo score final (para exibir na coluna sugestoes_topN)
        # sugestoes_formatadas = []
        # for idx2_sug, score_texto_sug, score_numero_sug, score_final_sug, score_bairro_sug in matches_final[:top_n]:
        #     endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2_original)
        #     numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
        #     score_final_str = f"{score_final_sug:.0f}" if score_final_sug is not None else "N/A"
        #     sugestoes_formatadas.append(
        #         f"{endereco_original} {numero} | Score Final: {score_final_str}"
        #     )

        # Para CADA match empatado, cria uma linha no resultado
        for (idx2, score_texto, score_numero, score_final, score_bairro) in melhores_matches:
            resultados.append({
                "idx_df1": idx1,
                "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1_original),
                "numero_df1": num1_int,
                "complemento_df1": formatar_endereco(
                    df1.loc[idx1],
                    colunas_complemento1
                ) if colunas_complemento1 else None,
                "bairro_df1": formatar_endereco(df1.loc[idx1], [col_bairro1_original]),
                "idx_df2": idx2,
                "cod_unico_df2": df2.at[idx2, cod_unico_endereco] if cod_unico_endereco else None,
                "endereco_df2": formatar_endereco(df2.iloc[idx2], colunas_logradouro2_original),
                "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
                "complemento_df2": formatar_endereco(
                    df2.loc[idx2],
                    colunas_complemento2
                ) if colunas_complemento2 else None,
                "bairro_df2": formatar_endereco(df2.loc[idx2], [col_bairro2_original]),
                "similaridade_logradouro": round(score_texto, 2) if score_texto is not None else None,
                "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
                "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
                "similaridade_final": round(score_final, 2) if score_final is not None else None,
                "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
                "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
                "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
                "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
                "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
                "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
            })

    return pd.DataFrame(resultados)
