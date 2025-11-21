import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from comparador import montar_logradouro, normalize_bairro, formatar_endereco

try:
    import faiss  # índice aproximado para acelerar busca
    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False


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
        das palavras. Por exemplo, 
        - "Av. Paulista" ≈ "Avenida Paulista".
        - "Rua das Flores" ≈ "Avenida das Flores"

    - Embeddings:
        Cada frase é convertida em um vetor numérico (ex: [0.13, -0.44, 0.95, ...]) 
        que representa seu sentido. Frases semelhantes geram vetores próximos.

        A similaridade entre dois textos é calculada pelo cosseno entre os vetores:
            1.0 - idênticos, 0.8 - parecidos, 0.2 - diferentes.

    Retorna:
        Um DataFrame com os melhores matches entre endereços e as top N sugestões.
    """

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
        
    def limpar_bairro_llm(b):
        for termo in ["jardim", "jd", "vila", "vl", "bairro", "jd.", "vl.", "pq.", "parque"]:
            b = b.replace(termo, "")
        return b.strip()
    
    # Parâmetros de desempenho (ajustáveis via kwargs)
    batch_encode = int(kwargs.get("batch_size", 64))  # tamanho do lote para gerar embeddings
    batch_consulta = int(kwargs.get("lote_consulta", 512))  # tamanho do lote para fazer buscas
    top_k_candidatos = int(kwargs.get("top_k_busca", max(top_n * 3, 20)))  # candidatos retornados pelo ANN/semantic_search
    tol = float(kwargs.get("tolerancia_logradouro", 0.001))  # tolerância em torno do melhor score
    show_progress = bool(kwargs.get("show_progress_bar", False))
    usar_faiss = bool(kwargs.get("usar_faiss", True)) and _HAS_FAISS

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

    # 🔹 Mantém cópia dos bairros originais (para exibir no resultado final)
    df1["bairro_original"] = df1[col_bairro1] if col_bairro1 else ""
    df2["bairro_original"] = df2[col_bairro2] if col_bairro2 else ""

    # Remove termos genéricos que atrapalham a similaridade semântica,
    # como “jardim”, “vila”, “bairro” etc.
    df1["bairro_normalizado"] = df1["bairro_normalizado"].apply(limpar_bairro_llm)
    df2["bairro_normalizado"] = df2["bairro_normalizado"].apply(limpar_bairro_llm)

    # Embeddings do conjunto de referência (df2) em lote para evitar estouro de memória
    emb2 = model.encode(
        df2["logradouro_normalizado"].tolist(),
        batch_size=batch_encode,
        convert_to_tensor=True,
        show_progress_bar=show_progress
    )
    emb_bairros2 = model.encode(
        df2["bairro_normalizado"].tolist(),
        batch_size=batch_encode,
        convert_to_tensor=True,
        show_progress_bar=False
    )

    index_faiss = None
    if usar_faiss:
        emb2_np = emb2.detach().cpu().numpy().astype("float32")
        faiss.normalize_L2(emb2_np)
        index_faiss = faiss.IndexFlatIP(emb2_np.shape[1])
        index_faiss.add(emb2_np)

    resultados = []

    # Loop principal em lotes: cada endereço de df1 consulta apenas top-k de df2 (semantic search via cosine)
    for inicio in range(0, len(df1), batch_consulta):
        fim = min(len(df1), inicio + batch_consulta)
        df1_lote = df1.iloc[inicio:fim]

        emb1_lote = model.encode(
            df1_lote["logradouro_normalizado"].tolist(),
            batch_size=batch_encode,
            convert_to_tensor=True,
            show_progress_bar=show_progress
        )
        emb_bairros1_lote = model.encode(
            df1_lote["bairro_normalizado"].tolist(),
            batch_size=batch_encode,
            convert_to_tensor=True,
            show_progress_bar=False
        )

        if index_faiss is not None:
            emb1_np = emb1_lote.detach().cpu().numpy().astype('float32')
            faiss.normalize_L2(emb1_np)
            scores, idxs = index_faiss.search(emb1_np, top_k_candidatos)
            candidatos_lote = [
                [
                    {'corpus_id': int(idx), 'score': float(score)}
                    for idx, score in zip(row_idx, row_score)
                ]
                for row_idx, row_score in zip(idxs, scores)
            ]
        else:
            # semantic_search já devolve top-k por query sem materializar a matriz completa
            candidatos_lote = util.semantic_search(
                emb1_lote, emb2, top_k=top_k_candidatos, score_function=util.cos_sim
            )

        for idx_local, candidatos in enumerate(candidatos_lote):
            idx1 = inicio + idx_local
            if not candidatos:
                continue

            # Filtra candidatos que empatam com o melhor dentro de uma tolerância
            melhor_score = max(c["score"] for c in candidatos)
            candidatos = [c for c in candidatos if c["score"] >= (melhor_score - tol)]

            num1_int = try_int(df1_lote.iloc[idx_local][col_num1]) if col_num1 else None
            bairro1 = df1_lote.iloc[idx_local]["bairro_normalizado"]

            matches_final = []
            for cand in candidatos:
                idx2 = cand["corpus_id"]
                score_log = float(cand["score"]) * 100  # 0..100
                num2_int = try_int(df2.iloc[idx2][col_num2]) if col_num2 else None
                bairro2 = df2.iloc[idx2]["bairro_normalizado"]

                # Número: distância relativa
                if num1_int is not None and num2_int is not None:
                    diff = abs(num1_int - num2_int)
                    if diff == 0:
                        score_num = 100
                    else:
                        maior = max(num1_int, num2_int)
                        score_num = max(0, 100 * (1 - diff / maior)) if maior else 0
                else:
                    score_num = None

                # Bairro via embeddings somente para candidatos
                if bairro1 or bairro2:
                    score_bairro = float(
                        util.cos_sim(emb_bairros1_lote[idx_local], emb_bairros2[idx2]).item()
                    ) * 100
                else:
                    score_bairro = None

                num_component = score_num if score_num is not None else score_log
                bairro_component = score_bairro if score_bairro is not None else score_log
                score_final = (
                    score_log * peso_logradouro +
                    num_component * peso_numero +
                    bairro_component * peso_bairro
                )

                matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

            if not matches_final:
                continue

            # Ordena e aplica preferência por número exato
            matches_final.sort(key=lambda x: x[4], reverse=True)
            melhor_atual = matches_final[0]
            preferir_numero_exato = True
            margem_override = 8
            if preferir_numero_exato:
                candidatos_exatos = [m for m in matches_final if m[2] == 100]
                if candidatos_exatos:
                    melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))
                    if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                        matches_final.remove(melhor_exato)
                        matches_final.insert(0, melhor_exato)

            idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

            sugestoes_formatadas = []
            for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
                endereco_original = formatar_endereco(
                    df2.iloc[idx2_sug],
                    colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
                )
                numero = df2.iloc[idx2_sug][col_num2] if col_num2 else ""
                sugestoes_formatadas.append(f"{endereco_original} {numero} | Score Final: {sc_final:.2f}")

            resultados.append({
                "idx_df1": idx1,
                "endereco_df1": formatar_endereco(
                    df1.iloc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])
                ),
                "numero_df1": df1.iloc[idx1][col_num1] if col_num1 else None,
                "bairro_df1": df1.iloc[idx1]["bairro_original"],
                "idx_df2": idx2,
                "endereco_df2": formatar_endereco(
                    df2.iloc[idx2], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else [])
                ),
                "numero_df2": df2.iloc[idx2][col_num2] if col_num2 else None,
                "bairro_df2": df2.iloc[idx2]["bairro_original"],
                "similaridade_logradouro": round(score_log, 2),
                "similaridade_numero": round(score_num, 2) if score_num is not None else None,
                "similaridade_bairro": round(score_bairro, 2) if score_bairro is not None else None,
                "similaridade_final": round(melhor_final, 2),
                "sugestoes_topN": "; ".join(sugestoes_formatadas)
            })

    return pd.DataFrame(resultados)
