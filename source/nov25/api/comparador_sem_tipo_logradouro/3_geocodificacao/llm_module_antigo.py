# import pandas as pd
# import torch
# from sentence_transformers import SentenceTransformer, util
# from comparador import montar_logradouro, normalize_bairro, formatar_endereco


# def executar_llm(
#     df1, df2,
#     colunas_logradouro1, colunas_logradouro2,
#     col_num1=None, col_num2=None,
#     col_bairro1=None, col_bairro2=None,
#     latitude=None, longitude=None, cd_setor=None,
#     top_n=5,
#     peso_logradouro=0.5,
#     peso_numero=0.4,
#     peso_bairro=0.1,
#     **kwargs
# ):

#     """
#     Compara endereços usando embeddings de linguagem (resultado numérico da LLM)  
#     (open source, modelo da Hugging Face)

#     - Modelo usado: "all-MiniLM-L6-v2"
#         Rede neural treinada em milhões de textos que entende o significado 
#         das palavras. Por exemplo, 
#         - "Av. Paulista" ≈ "Avenida Paulista".
#         - "Rua das Flores" ≈ "Avenida das Flores"

#     - Embeddings:
#         Cada frase é convertida em um vetor numérico (ex: [0.13, -0.44, 0.95, ...]) 
#         que representa seu sentido. Frases semelhantes geram vetores próximos.

#         A similaridade entre dois textos é calculada pelo cosseno entre os vetores:
#             1.0 - idênticos, 0.8 - parecidos, 0.2 - diferentes.

#     Retorna:
#         Um DataFrame com os melhores matches entre endereços e as top N sugestões.
#     """

#     def try_int(n):
#         """
#         Tenta converter um valor em número inteiro.
#         Retorna None se não for possível (exemplo: texto vazio).
#         """
#         if pd.isna(n):
#             return None
#         try:
#             return int(float(n))
#         except Exception:
#             return None
        
#     def limpar_bairro_llm(b):
#         for termo in ["jardim", "jd", "vila", "vl", "bairro", "jd.", "vl.", "pq.", "parque"]:
#             b = b.replace(termo, "")
#         return b.strip()
    
#     # Define onde o modelo vai rodar: CPU ou GPU
#     device = 'cuda' if torch.cuda.is_available() else 'cpu'

#     # Carrega o modelo de linguagem
#     model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)

#     # Cria cópias das tabelas originais
#     df1 = df1.copy()
#     df2 = df2.copy()

#     # Normaliza os endereços
#     df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
#     df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)
#     df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
#     df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

#     # 🔹 Mantém cópia dos bairros originais (para exibir no resultado final)
#     df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
#     df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

#     # Remove termos genéricos que atrapalham a similaridade semântica,
#     # como “jardim”, “vila”, “bairro” etc.
#     df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
#     df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

#     # Gera os embeddings (vetores numéricos) para os logradouros
#     # Quanto mais próximos dois vetores, mais semelhantes são os textos.
#     emb1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)
#     emb2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)

#     emb_bairros1 = model.encode(df1["bairro_normalizado"].tolist(), convert_to_tensor=True)
#     emb_bairros2 = model.encode(df2["bairro_normalizado"].tolist(), convert_to_tensor=True)

#     resultados = []
    
#     # Loop principal: compara cada endereço de df1 com todos de df2
#     for idx1, _ in enumerate(df1["logradouro_normalizado"]):

#         # Calcula a similaridade entre o embedding do endereço de df1
#         # e todos os embeddings de df2, usando "cosine similarity".
#         # Essa medida vai de 0 (muito diferente) a 1 (muito parecido).
#         cos_scores = util.cos_sim(emb1[idx1], emb2)[0]

#         # pegue todos os candidatos que estão praticamente empatados com o melhor
#         max_score = float(cos_scores.max().item())
#         tol = float(kwargs.get("tolerancia_logradouro", 0.001))  # 0.1% de tolerância por padrão
#         mask = cos_scores >= (max_score - tol)
#         idxs_candidatos = torch.nonzero(mask).flatten().tolist()

#         # Ordena os índices dos endereços de df2 do mais parecido para o menos parecido
#         ### indices_ordenados = torch.argsort(cos_scores, descending=True)

#         # Extrai número e bairro do endereço atual de df1
#         num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
#         bairro1 = df1.loc[idx1, "bairro_normalizado"]

#         matches_final = []

#         # Para cada endereço candidato (df2), calcula as pontuações
#         for idx2 in idxs_candidatos:
#             score_log = float(cos_scores[idx2].item()) * 100  # 0..100
#             num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
#             bairro2 = df2.loc[idx2, "bairro_normalizado"]

#             # O número do endereço é comparado de forma quantitativa
#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 if diff == 0:
#                     score_num = 100
#                 else:
#                     maior = max(num1_int, num2_int)
#                     score_num = max(0, 100 * (1 - diff / maior)) if maior else 0
#             else:
#                 score_num = None

#             # Os bairros também viram embeddings, e a similaridade é medida
#             # pelo cosseno entre os vetores, da mesma forma que os logradouros
#             if bairro1 or bairro2:
#                 score_bairro = float(util.cos_sim(emb_bairros1[idx1], emb_bairros2[idx2]).item()) * 100
#             else:
#                 score_bairro = None

#             # Soma ponderada dos scores
#             num_component = score_num if score_num is not None else score_log
#             bairro_component = score_bairro if score_bairro is not None else score_log
#             score_final = (
#                 score_log * peso_logradouro +
#                 num_component * peso_numero +
#                 bairro_component * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         if not matches_final:
#             continue

#         # Ordena primeiro pelos scores
#         matches_final.sort(key=lambda x: x[4], reverse=True)
#         melhor_atual = matches_final[0]

#         # Override para número exato:
#         # se houver número exato (100%), prioriza esse
#         # Isso ajuda a corrigir casos de ruas iguais com números diferentes.
#         preferir_numero_exato = True
#         margem_override = 8  # tolerância
#         if preferir_numero_exato:
#             candidatos_exatos = [m for m in matches_final if m[2] == 100]
#             if candidatos_exatos:
#                 melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
#                 if melhor_exato[4] >= (melhor_atual[4] - margem_override):
#                     matches_final.remove(melhor_exato)
#                     matches_final.insert(0, melhor_exato)

#         # Ordena os candidatos e escolhe o melhor match
#         idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

#         # Monta uma lista de sugestões (top N endereços mais parecidos)
#         sugestoes_formatadas = []
#         for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
#             endereco_original = formatar_endereco(
#                 df2.loc[idx2_sug],
#                 colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
#             )
#             numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
#             sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.2f}")

#         # Salva o resultado consolidado
#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
#             "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
#             "bairro_df1": df1.loc[idx1, "bairro_original"],
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])),
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "bairro_df2": df2.loc[idx2, "bairro_original"],
#             "similaridade_logradouro": round(score_log, 2),
#             "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_final, 2),
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "lat": df2.at[idx2, latitude] if latitude else None,
#             "long": df2.at[idx2, longitude] if longitude else None,
#             "cd_setor": df2.at[idx2, cd_setor] if cd_setor else None,
#         })

#     return pd.DataFrame(resultados)


# llm.py
# import os
# import pandas as pd
# import torch
# from sentence_transformers import SentenceTransformer, util
# from comparador import montar_logradouro, normalize_bairro, formatar_endereco, try_int

# # OPCIONAL: limitar threads internas do PyTorch/BLAS
# torch.set_num_threads(2)
# os.environ["OMP_NUM_THREADS"] = "2"


import os
import pandas as pd

# limitar threads de BLAS/torch para não surtar no WSL
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import torch

torch.set_num_threads(1)

from sentence_transformers import SentenceTransformer, util
from comparador import montar_logradouro, normalize_bairro, formatar_endereco, try_int

# def executar_llm(
#     df1, df2,
#     colunas_logradouro1, colunas_logradouro2,
#     col_num1=None, col_num2=None,
#     col_bairro1=None, col_bairro2=None,
#     latitude=None, longitude=None, cd_setor=None,
#     top_n=5,
#     peso_logradouro=0.5,
#     peso_numero=0.4,
#     peso_bairro=0.1,
#     **kwargs
# ):

#     def limpar_bairro_llm(b: str):
#         if pd.isna(b) or b is None:
#             return ""
#         b = str(b).lower()
#         for termo in ["jardim", "jd", "vila", "vl", "bairro", "jd.", "vl.", "pq.", "parque"]:
#             b = b.replace(termo, "")
#         return " ".join(b.split()).strip()

#     device = 'cuda' if torch.cuda.is_available() else 'cpu'
#     model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)

#     df1 = df1.copy()
#     df2 = df2.copy()

#     df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
#     df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

#     df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
#     df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

#     df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
#     df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

#     df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
#     df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

#     # embeddings
#     emb1 = model.encode(df1["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)
#     emb2 = model.encode(df2["logradouro_normalizado"].tolist(), convert_to_tensor=True, show_progress_bar=True)

#     emb_bairros1 = model.encode(df1["bairro_normalizado"].tolist(), convert_to_tensor=True)
#     emb_bairros2 = model.encode(df2["bairro_normalizado"].tolist(), convert_to_tensor=True)

#     tolerancia = float(kwargs.get("tolerancia_logradouro", 0.001))
#     resultados = []

#     # --------- LOOP SEQUENCIAL (sem threads) ----------
#     for idx1 in range(len(df1)):
#         cos_scores = util.cos_sim(emb1[idx1], emb2)[0]

#         max_score = float(cos_scores.max().item())
#         mask = cos_scores >= (max_score - tolerancia)
#         idxs_candidatos = torch.nonzero(mask).flatten().tolist()

#         num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
#         bairro1 = df1.loc[idx1, "bairro_normalizado"]

#         matches_final = []

#         for idx2 in idxs_candidatos:
#             score_log = float(cos_scores[idx2].item()) * 100
#             num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
#             bairro2 = df2.loc[idx2, "bairro_normalizado"]

#             # número
#             if num1_int is not None and num2_int is not None:
#                 diff = abs(num1_int - num2_int)
#                 if diff == 0:
#                     score_num = 100
#                 else:
#                     maior = max(num1_int, num2_int)
#                     score_num = max(0, 100 * (1 - diff / maior)) if maior else 0
#             else:
#                 score_num = None

#             # bairro
#             if bairro1 or bairro2:
#                 score_bairro = float(util.cos_sim(emb_bairros1[idx1], emb_bairros2[idx2]).item()) * 100
#             else:
#                 score_bairro = None

#             num_component = score_num if score_num is not None else score_log
#             bairro_component = score_bairro if score_bairro is not None else score_log

#             score_final = (
#                 score_log * peso_logradouro +
#                 num_component * peso_numero +
#                 bairro_component * peso_bairro
#             )

#             matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

#         if not matches_final:
#             continue

#         matches_final.sort(key=lambda x: x[4], reverse=True)
#         melhor_atual = matches_final[0]

#         # override número exato
#         preferir_numero_exato = True
#         margem_override = 8
#         if preferir_numero_exato:
#             candidatos_exatos = [m for m in matches_final if m[2] == 100]
#             if candidatos_exatos:
#                 melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
#                 if melhor_exato[4] >= (melhor_atual[4] - margem_override):
#                     matches_final.remove(melhor_exato)
#                     matches_final.insert(0, melhor_exato)

#         idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

#         sugestoes_formatadas = []
#         for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
#             endereco_original = formatar_endereco(
#                 df2.loc[idx2_sug],
#                 colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
#             )
#             numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
#             sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.2f}")

#         resultados.append({
#             "idx_df1": idx1,
#             "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
#             "numero_df1": df1.loc[idx1, col_num1] if col_num1 else None,
#             "bairro_df1": df1.loc[idx1, "bairro_original"],
#             "idx_df2": idx2,
#             "endereco_df2": formatar_endereco(df2.loc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])),
#             "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
#             "bairro_df2": df2.loc[idx2, "bairro_original"],
#             "similaridade_logradouro": round(score_log, 2),
#             "similaridade_numero": round(score_num, 2) if score_num is not None else None,
#             "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
#             "similaridade_final": round(melhor_final, 2),
#             "sugestoes_topN": "; ".join(sugestoes_formatadas),
#             "lat": df2.at[idx2, latitude] if latitude else None,
#             "long": df2.at[idx2, longitude] if longitude else None,
#             "cd_setor": df2.at[idx2, cd_setor] if cd_setor else None,
#         })

#     return pd.DataFrame(resultados)

def executar_llm(
    df1, df2,
    colunas_logradouro1, colunas_logradouro2,
    col_num1=None, col_num2=None,
    col_bairro1=None, col_bairro2=None,
    latitude_verdadeira=None, longitude_verdadeira=None, cd_setor_verdadeiro=None,
    latitude_resultante=None, longitude_resultante=None, cd_setor_resultante=None,
    top_n=5,
    peso_logradouro=0.5,
    peso_numero=0.4,
    peso_bairro=0.1,
    **kwargs
):
    import re
    import gc

    def limpar_bairro_llm(b: str):
        if pd.isna(b) or b is None:
            return ""
        b = str(b).lower()
        palavras_remover = [
            "jardim", "jd", "vila", "vl", "bairro",
            "loteamento", "loteam", "residencial", "res",
            "condomínio", "cond", "conjunto", "cj", "parque", "pq"
        ]
        for p in palavras_remover:
            b = b.replace(p, " ")
        b = re.sub(r"\s+", " ", b).strip()
        return b

    # ---------- Config de modelo / device ----------
    device = kwargs.get("device", "cpu")
    model_name = kwargs.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name, device=device)

    # Tamanho dos chunks (linhas de df1 por vez) e batch interno do encode
    chunk_size = int(kwargs.get("chunk_size", 500))
    batch_size = int(kwargs.get("batch_size", 32))

    print(f"[LLM] Usando modelo: {model_name} no device: {device}")
    print(f"[LLM] chunk_size={chunk_size}, batch_size={batch_size}")

    # ---------- Normalização de logradouros e bairros ----------
    print("[LLM] Normalizando logradouros e bairros...")
    df1 = df1.copy()
    df2 = df2.copy()

    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
    df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

    df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
    df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

    # ---------- Embeddings de df2 (referência) ----------
    print("[LLM] Gerando embeddings dos logradouros de df2 (referência)...")
    emb2_log = model.encode(
        df2["logradouro_normalizado"].tolist(),
        batch_size=batch_size,
        convert_to_tensor=True,
        show_progress_bar=True,
    )

    print("[LLM] Gerando embeddings dos bairros de df2 (referência)...")
    emb2_bairro = model.encode(
        df2["bairro_normalizado"].tolist(),
        batch_size=batch_size,
        convert_to_tensor=True,
        show_progress_bar=False,
    )

    tolerancia = float(kwargs.get("tolerancia_logradouro", 0.001))
    margem_override = float(kwargs.get("margem_override_numero", 5.0))

    resultados = []

    n1 = len(df1)
    print(f"[LLM] Iniciando processamento de df1 em chunks (total linhas: {n1})...")

    # ---------- Loop por chunks de df1 ----------
    for start in range(0, n1, chunk_size):
        end = min(start + chunk_size, n1)
        df1_chunk = df1.iloc[start:end].copy()
        idxs_chunk = df1_chunk.index.tolist()

        print(f"[LLM] Chunk {start}–{end} de {n1}...")

        # Embeddings de logradouro para o chunk de df1
        emb1_log_chunk = model.encode(
            df1_chunk["logradouro_normalizado"].tolist(),
            batch_size=batch_size,
            convert_to_tensor=True,
            show_progress_bar=True,
        )

        # Embeddings de bairro para o chunk de df1
        emb1_bairro_chunk = model.encode(
            df1_chunk["bairro_normalizado"].tolist(),
            batch_size=batch_size,
            convert_to_tensor=True,
            show_progress_bar=False,
        )

        # ---------- Loop linha a linha dentro do chunk ----------
        for local_i, idx1 in enumerate(idxs_chunk):
            cos_scores = util.cos_sim(emb1_log_chunk[local_i], emb2_log)[0]

            max_score = float(cos_scores.max().item())
            mask = cos_scores >= (max_score - tolerancia)
            idxs_candidatos = torch.nonzero(mask).flatten().tolist()

            num1_int = try_int(df1.loc[idx1, col_num1]) if col_num1 else None
            bairro1 = df1.loc[idx1, "bairro_normalizado"]

            matches_final = []

            for idx2 in idxs_candidatos:
                score_log = float(cos_scores[idx2].item()) * 100

                num2_int = try_int(df2.loc[idx2, col_num2]) if col_num2 else None
                bairro2 = df2.loc[idx2, "bairro_normalizado"]

                # Similaridade de número
                score_num = None
                if num1_int is not None and num2_int is not None:
                    diff = abs(num1_int - num2_int)
                    if diff == 0:
                        score_num = 100.0
                    elif diff <= 10:
                        score_num = max(0, 100 - diff * 10)
                    else:
                        score_num = 0.0

                # Similaridade de bairro (embeddings)
                if bairro1 and bairro2:
                    emb_b1_i = emb1_bairro_chunk[local_i].unsqueeze(0)
                    cos_bairros = util.cos_sim(
                        emb_b1_i,
                        emb2_bairro[idx2].unsqueeze(0)
                    ).item()
                    score_bairro = float(cos_bairros * 100)
                else:
                    score_bairro = 0.0

                # Combinação ponderada
                peso_log = float(peso_logradouro)
                peso_num = float(peso_numero) if score_num is not None else 0.0
                peso_bai = float(peso_bairro) if score_bairro is not None else 0.0

                soma_pesos = peso_log + peso_num + peso_bai
                if soma_pesos <= 0:
                    soma_pesos = 1.0

                score_final = (
                    (score_log * peso_log) +
                    (score_num or 0) * peso_num +
                    (score_bairro or 0) * peso_bai
                ) / soma_pesos

                matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

            # Ordena candidatos pelo score final
            matches_final.sort(key=lambda x: x[4], reverse=True)

            # Preferência por número exato, se existir
            if num1_int is not None and matches_final:
                candidatos_exatos = [
                    m for m in matches_final
                    if try_int(df2.loc[m[0], col_num2]) == num1_int
                ]
                if candidatos_exatos:
                    melhor_atual = matches_final[0]
                    melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
                    if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                        matches_final.remove(melhor_exato)
                        matches_final.insert(0, melhor_exato)

            if not matches_final:
                # Nenhum candidato (improvável, mas por segurança)
                continue

            idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

            # Monta topN sugestões formatadas
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
                "sugestoes_topN": "; ".join(sugestoes_formatadas),
                "latitude_verdadeira": df1.at[idx1, latitude_verdadeira] if latitude_verdadeira else None,
                "longitude_verdadeira": df1.at[idx1, longitude_verdadeira] if longitude_verdadeira else None,
                "cd_setor_verdadeiro": df1.at[idx1, cd_setor_verdadeiro] if cd_setor_verdadeiro else None,
                "latitude_resultante": df2.at[idx2, latitude_resultante] if latitude_resultante else None,
                "longitude_resultante": df2.at[idx2, longitude_resultante] if longitude_resultante else None,
                "cd_setor_resultante": df2.at[idx2, cd_setor_resultante] if cd_setor_resultante else None
            })

        # Libera memória do chunk
        del emb1_log_chunk, emb1_bairro_chunk, df1_chunk
        gc.collect()

    return pd.DataFrame(resultados)

