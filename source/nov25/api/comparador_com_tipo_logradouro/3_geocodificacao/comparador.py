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

    # Chama o algoritmo escolhido
    if algoritmo == "rapidfuzz":
        from rapidfuzz_module import executar_rapidfuzz

        return executar_rapidfuzz(
            df1, df2,
            "logradouro_normalizado", "logradouro_normalizado",
            colunas_logradouro1, colunas_logradouro2,
            "tipo_logradouro_normalizado", "tipo_logradouro_normalizado",  # << NOVO
            "numero_int", "numero_int",
            "bairro_normalizado", "bairro_normalizado",
            col_bairro1, col_bairro2,
            latitude_verdadeira, longitude_verdadeira, cd_setor_verdadeiro,
            latitude_resultante, longitude_resultante, cd_setor_resultante,
            cod_unico_endereco,
            **kwargs
        )

    elif algoritmo == "llm": 
        from llm_module import executar_llm
        return executar_llm(
            df1, df2,
            colunas_logradouro1, colunas_logradouro2,
            col_num1=col_num1, col_num2=col_num2,
            col_bairro1=col_bairro1, col_bairro2=col_bairro2,
            latitude_verdadeira=latitude_verdadeira, longitude_verdadeira=longitude_verdadeira, cd_setor_verdadeiro=cd_setor_verdadeiro,
            latitude_resultante=latitude_resultante, longitude_resultante=longitude_resultante, cd_setor_resultante=cd_setor_resultante,
            **kwargs
        )
    elif algoritmo == "elasticsearch":
        from elasticsearch_module import executar_elasticsearch # funcao atualizada
        return executar_elasticsearch(
            df1, df2,
            "logradouro_normalizado", "logradouro_normalizado", 
            colunas_logradouro1, colunas_logradouro2,
            "tipo_logradouro_normalizado", "tipo_logradouro_normalizado",
            "numero_int", "numero_int",
            "bairro_normalizado", "bairro_normalizado",
            col_bairro1_original=col_bairro1, col_bairro2_original=col_bairro2,
            latitude_verdadeira=latitude_verdadeira, longitude_verdadeira=longitude_verdadeira, cd_setor_verdadeiro=cd_setor_verdadeiro,
            latitude_resultante=latitude_resultante, longitude_resultante=longitude_resultante, cd_setor_resultante=cd_setor_resultante,
            cod_unico_endereco=cod_unico_endereco,
            **kwargs)

    else:
        raise ValueError("Algoritmo inválido. Escolha 'rapidfuzz' ou 'llm' ou 'elasticsearch'.")

