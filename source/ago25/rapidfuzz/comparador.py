import pandas as pd
from rapidfuzz import process, fuzz
import unidecode
from num2words import num2words
import re

"""
Este código utiliza a biblioteca RapidFuzz para comparar endereços entre dois DataFrames
e encontrar o melhor "match" entre eles.

Objetivo:
    - Receber dois conjuntos de endereços (df1 e df2).
    - Normalizar os textos (tirar acentos, abreviações e tipos de logradouro).
    - Calcular a similaridade entre os endereços de df1 e os de df2.
    - Retornar o melhor match e sugestões alternativas, considerando:
        (a) Similaridade textual do logradouro.
        (b) Similaridade numérica do número do endereço.

Como a similaridade textual é calculada:
    - Usa a função fuzz.token_set_ratio do RapidFuzz.
    - Essa função divide o texto em tokens (palavras), ignora a ordem e compara os conjuntos.
    - Exemplo: "Rua das Flores" vs "Flores Rua das" → 100 (iguais).
    - Internamente, a comparação usa a distância de edição de Levenshtein,
      que mede o número mínimo de operações (inserção, remoção, substituição)
      necessárias para transformar uma string em outra.

Como o score final é definido:
    - Similaridade final = (peso_texto * score_texto) + (peso_numero * score_numero).
    - Se não houver número disponível, considera apenas o texto.

Resultado:
    - Para cada endereço em df1, o código retorna:
        * Melhor correspondência em df2.
        * Scores de similaridade (texto, número e final).
        * Lista das Top N sugestões mais próximas.
"""

def normalize(text):
    """
    Remove acentos, coloca tudo em minúsculas e tira espaços extras
    """
    if pd.isna(text):
        return ""
    return unidecode.unidecode(str(text)).strip().lower()

def normalizar_abreviacoes(texto):
    """
    Substitui abreviações comuns de logradouros para forma completa
    """
    abreviacoes = {
        " av ": " avenida ",  
        " avn ": " avenida ",
        " r ": " rua ",
        " pc ": " praca ",
        " al ": " alameda ",
        " tr ": " travessa ",
        " jd ": " jardim ",
        " vl ": " vila ",
        " prq ": " parque ",
        " jdm ": " jardim ",
        " pq ": " parque ",
        " vil ": " vila "
    }
    texto = " " + texto + " "
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()

def numeros_para_texto(texto):
    """
    Substitui números inteiros no texto por palavras.
    Ex: "Rua 22 de Abril" -> "Rua vinte e dois de Abril"
    """
    def substituir(match):
        num = int(match.group())
        return num2words(num, lang='pt')
    
    return re.sub(r'\b\d+\b', substituir, texto)

def remover_tipo_logradouro(texto):
    """
    Remove tipos de logradouro (RUA, AVENIDA, ALAMEDA...) apenas para comparação textual.
    """
    tipos = ["acesso", "alameda", "avenida", "calcada", "chacara", "condominio", "corredor", "entrada", "escadao", "escadaria", "faixa", "passagem", "praca", "rodovia", "rua", "saida", "serra", "travessa", "travessao", "travessia", "viela"]
    texto = " " + texto.lower() + " "
    for t in tipos:
        texto = texto.replace(f" {t} ", " ")
    return texto.strip()

def montar_logradouro(df, colunas, excluir_col_num=None):
    """
    Concatena colunas que formam o logradouro (sem bairro) e aplica normalização.
    """
    def concat_normaliza(row):
        partes = []
        for col in colunas:
            if col == excluir_col_num:
                continue
            val = row.get(col, "")
            if pd.isna(val) or str(val).strip() == "":
                val = ""
            else:
                val = str(val)
            partes.append(val)
        texto = " ".join(partes)
        texto = numeros_para_texto(texto)
        texto = normalize(texto)
        texto = normalizar_abreviacoes(texto)
        texto = remover_tipo_logradouro(texto)
        return texto
    return df.apply(concat_normaliza, axis=1)

def normalize_bairro(df, col_bairro):
    """
    Normaliza apenas a coluna de bairro.
    """
    if col_bairro is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[col_bairro].fillna("").apply(lambda x: normalizar_abreviacoes(normalize(str(x))))

def formatar_endereco(row, colunas):
    """
    Monta o endereço original para exibição, concatenando as colunas especificadas,
    exatamente como está na base de dados.
    """
    partes = []
    for col in colunas:
        val = row.get(col, "")
        if pd.isna(val) or str(val).strip() == "":
            partes.append("")
        else:
            partes.append(str(val))
    return " ".join(partes).strip()

def comparar_enderecos(df1, df2,
                       colunas_logradouro1, colunas_logradouro2,
                       col_num1=None, col_num2=None,
                       col_bairro1=None, col_bairro2=None,
                       limiar_similaridade=85,
                       peso_logradouro=0.65, peso_numero=0.30, peso_bairro=0.05,
                       top_n=5):
    
    """
    Compara endereços entre dois DataFrames considerando:
        - Similaridade textual entre nomes de logradouros.
        - Diferença numérica entre os números do logradouro.

    Lógica do algoritmo:
    1. Normaliza e padroniza endereços em ambos os DataFrames.
    2. Para cada endereço do df1:
        a. Busca todos os endereços similares no df2 usando RapidFuzz.
        b. Calcula a similaridade textual.
        c. Calcula a similaridade numérica (considerando distância máxima).
        d. Combina as duas similaridades em um score final.
        e. Ordena e seleciona o melhor match e top N sugestões.
    """
    
    df1 = df1.copy() # DataFrame com os endereços que você quer procurar.  
    df2 = df2.copy() # DataFrame com os endereços que servirão de referência para a busca.  

    # Normalização
    df1["logradouro_normalizado"] = montar_logradouro(df1, colunas_logradouro1, excluir_col_num=col_num1)
    df2["logradouro_normalizado"] = montar_logradouro(df2, colunas_logradouro2, excluir_col_num=col_num2)

    df1["bairro_normalizado"] = normalize_bairro(df1, col_bairro1)
    df2["bairro_normalizado"] = normalize_bairro(df2, col_bairro2)

    resultados = []

    def try_int(n):
        """
        Converte valores para inteiro quando possível.
        """
        if pd.isna(n):
            return None
        n_str = str(n).strip()
        if n_str == "":
            return None
        try:
            return int(float(n_str))
        except:
            return None

    # Loop principal: percorre todos os endereços do df1
    for idx1, endereco1 in df1["logradouro_normalizado"].items():

        # Busca candidatos pelo logradouro
        matches_all = process.extract(
            endereco1,
            df2["logradouro_normalizado"],
            # fuzz.token_set_ratio: ignora a ordem das palavras e considera apenas o conjunto de tokens
            scorer=fuzz.token_set_ratio, 
            limit=None # retorna todos os matches possíveis
        )

        num1 = df1.loc[idx1, col_num1] if col_num1 else None
        num1_int = try_int(num1)
        bairro1 = df1.loc[idx1, "bairro_normalizado"]

        matches_final = []
        for log2_texto, score_log, idx2 in matches_all:
            num2 = df2.loc[idx2, col_num2] if col_num2 else None
            num2_int = try_int(num2)
            bairro2 = df2.loc[idx2, "bairro_normalizado"]

            # Similaridade numérica
            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_num = 100
                else:
                    score_num = max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_num = None

            # Similaridade de bairro
            score_bairro = fuzz.token_set_ratio(bairro1, bairro2) if bairro1 or bairro2 else None

            # Score final
            score_final = (
                score_log * peso_logradouro +
                (score_num if score_num is not None else score_log) * peso_numero +
                (score_bairro if score_bairro is not None else score_log) * peso_bairro
            )

            matches_final.append((idx2, score_log, score_num, score_bairro, score_final))

        # Ordena
        matches_final.sort(key=lambda x: x[4], reverse=True)

        # Override: promove número exato
        preferir_numero_exato = True
        margem_override = 8

        if preferir_numero_exato:
            # pega candidatos com número exato (score_num == 100)
            candidatos_exatos = [m for m in matches_final if m[2] == 100]
            if candidatos_exatos:
                melhor_exato = max(candidatos_exatos, key=lambda x: (x[1], x[4]))  # prioriza logradouro e score_final
                melhor_atual = matches_final[0]
                if melhor_exato[4] >= (melhor_atual[4] - margem_override):
                    matches_final.remove(melhor_exato)
                    matches_final.insert(0, melhor_exato)

        # Melhor match
        idx2, score_log, score_num, score_bairro, melhor_final = matches_final[0]

        # Sugestões
        sugestoes_formatadas = []
        for idx2_sug, sc_log, sc_num, sc_bai, sc_final in matches_final[:top_n]:
            endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas_logradouro2 + ([col_bairro2] if col_bairro2 else []))
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            sugestoes_formatadas.append(
                f"{endereco_original} {numero} | Score Final: {sc_final:.0f}"
            )

        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas_logradouro1 + ([col_bairro1] if col_bairro1 else [])),
            "numero_df1": num1,
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
