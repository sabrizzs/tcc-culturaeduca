import pandas as pd
from rapidfuzz import process, fuzz
import unidecode
from num2words import num2words
import re


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
        " vl ": " vila "
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
    
    # Substitui todos os números inteiros
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

def montar_endereco(df, colunas, excluir_col_num=None):
    """
    Concatena as colunas que contém as partes do endereço em uma string única
    e aplica normalização de texto e abreviações.
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

def possivel_bairro_diferente(end1, end2, score_final, penalizacao=0.95):
    """
    Penaliza o score final se os últimos tokens (possíveis bairros) forem diferentes.
    """
    tokens1 = end1.split()
    tokens2 = end2.split()
    
    if tokens1 and tokens2:
        ult1, ult2 = tokens1[-1], tokens2[-1]
        if ult1 != ult2:  # se o último token for diferente -> provável bairro diferente
            return score_final * penalizacao
    return score_final

def comparar_enderecos(df1, df2, colunas1, colunas2,
                       col_num1=None, col_num2=None,
                       limiar_similaridade=85, peso_texto=0.7, peso_numero=0.3,
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

    df1["endereco_normalizado"] = montar_endereco(df1, colunas1, excluir_col_num=col_num1)
    df2["endereco_normalizado"] = montar_endereco(df2, colunas2, excluir_col_num=col_num2)

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
    for idx1, endereco1 in df1["endereco_normalizado"].items():

        # Busca todos os matches textuais no df2
        matches_all = process.extract(
            endereco1,
            df2["endereco_normalizado"],
            # fuzz.token_set_ratio: ignora a ordem das palavras e considera apenas o conjunto de tokens
            scorer=fuzz.token_set_ratio, 
            limit=None # retorna todos os matches possíveis
        )

        num1 = df1.loc[idx1, col_num1] if col_num1 else None
        num1_int = try_int(num1)

        matches_final = []
        for endereco2_texto, score_texto, idx2 in matches_all:
            num2 = df2.loc[idx2, col_num2] if col_num2 else None
            num2_int = try_int(num2)

            if num1_int is not None and num2_int is not None:
                diff = abs(num1_int - num2_int)
                if diff == 0:
                    score_numero = 100
                else:
                    # Similaridade baseada em quão próximos estão
                    score_numero = max(0, 100 * (1 - diff / max(num1_int, num2_int)))
            else:
                score_numero = None

            
            if score_numero is None:
                # Ajusta o score final: se número ausente, considera só o texto
                score_final = score_texto
            else:
                # Combina similaridade de texto e número com pesos
                score_final = score_texto * peso_texto + score_numero * peso_numero

            score_final = possivel_bairro_diferente(endereco1, endereco2_texto, score_final)

            matches_final.append((idx2, score_texto, score_numero, score_final))

        # Ordena pelo score final
        matches_final.sort(key=lambda x: x[3], reverse=True)

        # Melhor match
        idx2, score_texto, score_numero, melhor_score_final = matches_final[0]

        # Sugestões top N pelo score final
        sugestoes_formatadas = []
        for idx2_sug, score_texto_sug, score_numero_sug, score_final_sug in matches_final[:top_n]:
            endereco_original = formatar_endereco(df2.loc[idx2_sug], colunas2)
            
            # Adiciona o número
            numero = df2.loc[idx2_sug, col_num2] if col_num2 else ""
            
            score_final_str = f"{score_final_sug:.0f}" if score_final_sug is not None else "N/A"

            sugestoes_formatadas.append(
                f"{endereco_original} {numero} | Score Final: {score_final_str}"
            )


        # Armazena o resultado no DataFrame final
        resultados.append({
            "idx_df1": idx1,
            "endereco_df1": formatar_endereco(df1.loc[idx1], colunas1),
            "numero_df1": num1,
            "idx_df2": idx2,
            "endereco_df2": formatar_endereco(df2.iloc[idx2], colunas2),
            "numero_df2": df2.loc[idx2, col_num2] if col_num2 else None,
            "similaridade_texto": round(score_texto, 2),
            "similaridade_numero": round(score_numero, 2) if score_numero is not None else None,
            "similaridade_final": round(melhor_score_final, 2) if melhor_score_final is not None else None,
            "sugestoes_topN": "; ".join(sugestoes_formatadas)
        })

    return pd.DataFrame(resultados)
