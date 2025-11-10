import pandas as pd
import unidecode
from num2words import num2words
import re

"""
Preparação de endereços

Responsabilidades:
1. Normalizar logradouros e bairros.
2. Converter números para texto.
3. Formatar endereços originais.
4. Preparar dados para envio ao algoritmo de comparação.
"""

# -------------------
# Funções de normalização
# -------------------

def normalize(text: str) -> str:
    """Remove acentos, coloca tudo em minúsculas e remove espaços extras"""
    if pd.isna(text):
        return ""
    return unidecode.unidecode(str(text)).strip().lower()

def normalizar_abreviacoes(texto: str) -> str:
    """Substitui abreviações comuns por forma completa"""
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
    texto = f" {texto} "
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()

def numeros_para_texto(texto: str) -> str:
    """Substitui números inteiros no texto por palavras"""
    def substituir(match):
        num = int(match.group())
        return num2words(num, lang='pt')
    return re.sub(r'\b\d+\b', substituir, texto)

def remover_tipo_logradouro(texto: str) -> str:
    """Remove tipos de logradouro apenas para comparação textual"""
    tipos = [
        "acesso", "alameda", "avenida", "calcada", "chacara", "condominio", 
        "corredor", "entrada", "escadao", "escadaria", "faixa", "passagem", 
        "praca", "rodovia", "rua", "saida", "serra", "travessa", "travessao", 
        "travessia", "viela"
    ]
    texto = f" {texto.lower()} "
    for t in tipos:
        texto = texto.replace(f" {t} ", " ")
    return texto.strip()

# -------------------
# Funções de montagem de endereço
# -------------------

def montar_logradouro(df: pd.DataFrame, colunas: list, excluir_col_num: str = None) -> pd.Series:
    """Concatena colunas que formam o logradouro (sem bairro) e aplica normalização"""
    def concat_normaliza(row):
        partes = []
        for col in colunas:
            if col == excluir_col_num:
                continue
            val = row.get(col, "")
            if pd.isna(val) or str(val).strip() == "":
                val = ""
            partes.append(str(val))
        texto = " ".join(partes)
        texto = numeros_para_texto(texto)
        texto = normalize(texto)
        texto = normalizar_abreviacoes(texto)
        # texto = remover_tipo_logradouro(texto)
        return texto
    return df.apply(concat_normaliza, axis=1)

def normalize_bairro(df: pd.DataFrame, col_bairro: str) -> pd.Series:
    """Normaliza a coluna de bairro"""
    if col_bairro is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[col_bairro].fillna("").apply(lambda x: normalizar_abreviacoes(normalize(str(x))))

def normalize_simples(df: pd.DataFrame, coluna: str) -> pd.Series:
    """Trata valores NaN e, chamando o normalize, remove acentos, espaços extras e coloca em minúsculas"""
    if coluna is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[coluna].fillna("").apply(lambda x: normalize(str(x)))

# -------------------
# Funções utilitárias
# -------------------

def try_int(n):
    """Converte valor para inteiro quando possível"""
    if pd.isna(n):
        return None
    n_str = str(n).strip()
    if n_str == "":
        return None
    try:
        return int(float(n_str))
    except:
        return None
    
def preparar_dataframe(df: pd.DataFrame, 
                       colunas_logradouro: list, 
                       col_num: str = None, 
                       col_bairro: str = None,
                       col_municipio: str = None,
                       col_sigla_uf: str = None) -> pd.DataFrame:
    """
    Prepara DataFrame para comparação:
    - Normaliza logradouro e bairro
    - Converte número para inteiro
    """
    df = df.copy()
    df["logradouro_normalizado"] = montar_logradouro(df, colunas_logradouro, excluir_col_num=col_num)
    df["bairro_normalizado"] = normalize_bairro(df, col_bairro)
    df["municipio_normalizado"] = normalize_simples(df, col_municipio)
    df["sigla_uf_normalizado"] = normalize_simples(df, col_sigla_uf)

    if col_num:
        df["numero_int"] = df[col_num].apply(lambda x: try_int(x)).astype("Int64")
    else:
        df["numero_int"] = None

    return df

# -------------------
# Função de comparação principal (chama módulo externo)
# -------------------

def limpar(df: pd.DataFrame, 
             colunas_logradouro: list,
             col_num: str = None,
             col_bairro: str = None,
             col_municipio: str = None,
             col_sigla_uf: str = None) -> pd.DataFrame:
    """
    Função principal para limpar endereços
    - df: DataFrame
    - colunas_logradouro: listas de colunas que compõem o logradouro
    - col_num: coluna de número do logradouro
    - col_bairro: coluna de bairro
    """
    # Prepara DataFrames
    df_preparado = preparar_dataframe(df, colunas_logradouro, col_num, col_bairro, col_municipio, col_sigla_uf)
    return pd.DataFrame(df_preparado)

import pandas as pd
from datetime import datetime
import time
import os

def main():
    """
    Run comparador - script principal
    Responsabilidades:
    1. Carregar arquivos de entrada.
    2. Configurar colunas de logradouro, número e bairro.
    3. Gerar dados limpos e salvar Excel.
    """

    # -------------------
    # Configurações do usuário
    # -------------------

    # Arquivos de entrada
    arquivo = "saude_2025.csv"

    # Colunas
    colunas_logradouro_arquivo = ["no_logradouro"]

    coluna_bairro_arquivo = "no_bairro"

    coluna_numero_arquivo = "nu_endereco"

    coluna_municipio_arquivo = "nm_mun"

    coluna_sigla_uf = "sigla_uf"


    # -------------------
    # Execução
    # -------------------

    start_time = time.time()

    # Carrega dados
    df = pd.read_csv(arquivo, sep=";", dtype=str)

    # Executa a comparação
    df_resultados = limpar(
        df,
        colunas_logradouro=colunas_logradouro_arquivo,
        col_num=coluna_numero_arquivo,
        col_bairro=coluna_bairro_arquivo,
        col_municipio=coluna_municipio_arquivo,
        col_sigla_uf=coluna_sigla_uf
    )

    # Exporta Excel
    # Exporta CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"result_{timestamp}.csv"

    df_resultados.to_csv(nome_arquivo, index=False, sep=";")  # sep=";" se quiser ponto e vírgula

    elapsed = time.time() - start_time
    print(f"Comparação concluída e arquivo salvo em {nome_arquivo}.")
    print(f"Tempo de execução: {elapsed:.2f} segundos.")

if __name__ == '__main__':
    main()