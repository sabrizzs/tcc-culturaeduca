# comparador.py
import pandas as pd
import unidecode
from num2words import num2words
import re

"""
comparador.py - Núcleo de preparação de endereços

Responsabilidades:
1. Normalizar logradouros e bairros.
2. Converter números para texto.
3. Formatar endereços originais.
4. Preparar dados para envio ao algoritmo de comparação.
"""

# -------------------
# Funções de normalização
# -------------------

# def normalize(text: str) -> str:
#     """Remove acentos, coloca tudo em minúsculas e remove espaços extras"""
#     if pd.isna(text):
#         return ""
#     return unidecode.unidecode(str(text)).strip().lower()

# def normalizar_abreviacoes(texto: str) -> str:
#     """Substitui abreviações comuns por forma completa"""
#     abreviacoes = {
#         " av ": " avenida ",
#         " avn ": " avenida ",
#         " r ": " rua ",
#         " pc ": " praca ",
#         " al ": " alameda ",
#         " tr ": " travessa ",
#         " jd ": " jardim ",
#         " vl ": " vila ",
#         " prq ": " parque ",
#         " jdm ": " jardim ",
#         " pq ": " parque ",
#         " vil ": " vila "
#     }
#     texto = f" {texto} "
#     for abrev, completo in abreviacoes.items():
#         texto = texto.replace(abrev, completo)
#     return texto.strip()

# def numeros_para_texto(texto: str) -> str:
#     """Substitui números inteiros no texto por palavras"""
#     def substituir(match):
#         num = int(match.group())
#         return num2words(num, lang='pt')
#     return re.sub(r'\b\d+\b', substituir, texto)

# def remover_tipo_logradouro(texto: str) -> str:
#     """Remove tipos de logradouro apenas para comparação textual"""
#     tipos = [
#         "acesso", "alameda", "avenida", "calcada", "chacara", "condominio", 
#         "corredor", "entrada", "escadao", "escadaria", "faixa", "passagem", 
#         "praca", "rodovia", "rua", "saida", "serra", "travessa", "travessao", 
#         "travessia", "viela"
#     ]
#     texto = f" {texto.lower()} "
#     for t in tipos:
#         texto = texto.replace(f" {t} ", " ")
#     return texto.strip()

# -------------------
# Funções de montagem de endereço
# -------------------

# def montar_logradouro(df: pd.DataFrame, colunas: list, excluir_col_num: str = None) -> pd.Series:
#     """Concatena colunas que formam o logradouro (sem bairro) e aplica normalização"""
#     def concat_normaliza(row):
#         partes = []
#         for col in colunas:
#             if col == excluir_col_num:
#                 continue
#             val = row.get(col, "")
#             if pd.isna(val) or str(val).strip() == "":
#                 val = ""
#             partes.append(str(val))
#         texto = " ".join(partes)
#         texto = numeros_para_texto(texto)
#         texto = normalize(texto)
#         texto = normalizar_abreviacoes(texto)
#         texto = remover_tipo_logradouro(texto)
#         return texto
#     return df.apply(concat_normaliza, axis=1)

# def normalize_bairro(df: pd.DataFrame, col_bairro: str) -> pd.Series:
#     """Normaliza a coluna de bairro"""
#     if col_bairro is None:
#         return pd.Series([""] * len(df), index=df.index)
#     return df[col_bairro].fillna("").apply(lambda x: normalizar_abreviacoes(normalize(str(x))))


# def normalize_setor_censitario(df: pd.DataFrame, col_cd_setor: str) -> pd.Series:
#     """Retira a última letra do cd_setor se houver, mas mantém NaN/None."""
#     return (
#         df[col_cd_setor]
#         .astype("string")  # tipo nativo string (aceita <NA>)
#         .str.replace(r"[A-Za-z]$", "", regex=True)
#     )


def formatar_endereco(row: pd.Series, colunas: list) -> str:
    """Monta o endereço original para exibição"""
    partes = []
    for col in colunas:
        val = row.get(col, "")
        if pd.isna(val) or str(val).strip() == "":
            partes.append("")
        else:
            partes.append(str(val))
    return " ".join(partes).strip()

# -------------------
# Funções utilitárias
# -------------------

# def preparar_dataframe(df: pd.DataFrame, 
#                        colunas_logradouro: list, 
#                        col_num: str = None, 
#                        col_bairro: str = None,
#                        col_cd_setor: str = None) -> pd.DataFrame:
#     """
#     Prepara DataFrame para comparação:
#     - Normaliza logradouro e bairro
#     - Converte número para inteiro
#     """
#     df = df.copy()
#     df["logradouro_normalizado"] = montar_logradouro(df, colunas_logradouro, excluir_col_num=col_num)
#     df["bairro_normalizado"] = normalize_bairro(df, col_bairro)
#     df[col_cd_setor] = normalize_setor_censitario(df, col_cd_setor)

#     if col_num:
#         df["numero_int"] = df[col_num].apply(lambda x: try_int(x))
#     else:
#         df["numero_int"] = None

#     return df

# def try_int(n):
#     """Converte valor para inteiro quando possível"""
#     if pd.isna(n):
#         return None
#     n_str = str(n).strip()
#     if n_str == "":
#         return None
#     try:
#         return int(float(n_str))
#     except:
#         return None

# -------------------
# Função de comparação principal (chama módulo externo)
# -------------------

def comparar(df1: pd.DataFrame, df2: pd.DataFrame, 
             colunas_logradouro1: list, colunas_logradouro2: list,
             col_num1: str = None, col_num2: str = None,
             col_bairro1: str = None, col_bairro2: str = None,
             latitude_verdadeira: str = None, longitude_verdadeira: str = None, cd_setor_verdadeiro: str = None,
             latitude_resultante: str = None, longitude_resultante: str = None, cd_setor_resultante: str = None,
             cod_unico_endereco: str = None,
             algoritmo: str = "llm", **kwargs) -> pd.DataFrame:
    """
    Função principal para comparar endereços
    - df1, df2: DataFrames
    - colunas_logradouro1/2: listas de colunas que compõem o logradouro
    - col_num1/2: coluna de número do logradouro
    - col_bairro1/2: coluna de bairro
    - algoritmo: 'rapidfuzz' ou 'llm'
    - kwargs: parâmetros específicos do algoritmo
    """
    # Prepara DataFrames
    # df1_preparado = preparar_dataframe(df1, colunas_logradouro1, col_num1, col_bairro1, cd_setor_verdadeiro)
    # df2_preparado = preparar_dataframe(df2, colunas_logradouro2, col_num2, col_bairro2, cd_setor_resultante)

    # Chama o algoritmo escolhido
    if algoritmo == "rapidfuzz":
        from rapidfuzz_module import executar_rapidfuzz # funcao atualizada
        if algoritmo == "rapidfuzz":
            return executar_rapidfuzz(
                df1, df2,
                "logradouro_normalizado", "logradouro_normalizado", 
                colunas_logradouro1, colunas_logradouro2,
                "numero_int", "numero_int",
                "bairro_normalizado", "bairro_normalizado",
                col_bairro1, col_bairro2,
                latitude_verdadeira, longitude_verdadeira, cd_setor_verdadeiro,
                latitude_resultante, longitude_resultante, cd_setor_resultante,
                cod_unico_endereco,
                **kwargs
            )
    # elif algoritmo == "llm":
    #     from llm_module import executar_llm
    #     return executar_llm(
    #         df1, df2,
    #         colunas_logradouro1, colunas_logradouro2,
    #         col_num1=col_num1, col_num2=col_num2,
    #         col_bairro1=col_bairro1, col_bairro2=col_bairro2,
    #         latitude_verdadeira=latitude_verdadeira, longitude_verdadeira=longitude_verdadeira, cd_setor_verdadeiro=cd_setor_verdadeiro,
    #         latitude_resultante=latitude_resultante, longitude_resultante=longitude_resultante, cd_setor_resultante=cd_setor_resultante,
    #         **kwargs
    #     )
    elif algoritmo == "llm":
        print('no llm')
        from llm_module import executar_llm
        # return executar_llm(
        #     df1, df2,
        #     "logradouro_normalizado", "logradouro_normalizado", 
        #     colunas_logradouro1, colunas_logradouro2,
        #     "numero_int", "numero_int",
        #     "bairro_normalizado", "bairro_normalizado",
        #     col_bairro1=col_bairro1, col_bairro2=col_bairro2,
        #     latitude_verdadeira=latitude_verdadeira, longitude_verdadeira=longitude_verdadeira, cd_setor_verdadeiro=cd_setor_verdadeiro,
        #     latitude_resultante=latitude_resultante, longitude_resultante=longitude_resultante, cd_setor_resultante=cd_setor_resultante,
        #     cod_unico_endereco=cod_unico_endereco,
        #     **kwargs
        # )
        return executar_llm(
            df1, df2,
            colunas_logradouro1,
            colunas_logradouro2,
            colunas_logradouro1_original=colunas_logradouro1,
            colunas_logradouro2_original=colunas_logradouro2,
            col_num1=col_num1,
            col_num2=col_num2,
            col_bairro1=col_bairro1,
            col_bairro2=col_bairro2,
            col_bairro1_original=col_bairro1,
            col_bairro2_original=col_bairro2,
            latitude_verdadeira=latitude_verdadeira,
            longitude_verdadeira=longitude_verdadeira,
            cd_setor_verdadeiro=cd_setor_verdadeiro,
            latitude_resultante=latitude_resultante,
            longitude_resultante=longitude_resultante,
            cd_setor_resultante=cd_setor_resultante,
            cod_unico_endereco=cod_unico_endereco,
            **kwargs
        )

    elif algoritmo == "elasticsearch":
        from elasticsearch_module import executar_elasticsearch # funcao atualizada
        return executar_elasticsearch(
            df1, df2,
            "logradouro_normalizado", "logradouro_normalizado", 
            colunas_logradouro1, colunas_logradouro2,
            "numero_int", "numero_int",
            "bairro_normalizado", "bairro_normalizado",
            col_bairro1_original=col_bairro1, col_bairro2_original=col_bairro2,
            latitude_verdadeira=latitude_verdadeira, longitude_verdadeira=longitude_verdadeira, cd_setor_verdadeiro=cd_setor_verdadeiro,
            latitude_resultante=latitude_resultante, longitude_resultante=longitude_resultante, cd_setor_resultante=cd_setor_resultante,
            cod_unico_endereco=cod_unico_endereco,
            **kwargs)

    else:
        raise ValueError("Algoritmo inválido. Escolha 'rapidfuzz' ou 'llm' ou 'elasticsearch'.")

