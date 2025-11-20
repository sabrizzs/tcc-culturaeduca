# run_comparador.py
import pandas as pd
from datetime import datetime
from comparador import comparar
import time
import os

"""
Run comparador - script principal
Responsabilidades:
1. Carregar arquivos de entrada.
2. Configurar colunas de logradouro, número e bairro.
3. Executar a comparação (RapidFuzz ou LLM).
4. Gerar resumo de similaridade e salvar Excel.
"""

# -------------------
# Configurações do usuário - Dados de Entrada
# -------------------

import argparse
import unicodedata
import re

# normaliza o paramentro de entrada local_base_dados
def normalizar(texto: str) -> str:
    # remove acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    # tudo minúsculo
    texto = texto.lower()
    # troca qualquer sequência de espaços por underline
    texto = re.sub(r'\s+', '_', texto)
    return texto


# le arquivo de entrada
parser = argparse.ArgumentParser(fromfile_prefix_chars='@')


parser.add_argument("--algoritmo", type=str, required=True, help="algoritmo que será utilizado: rapidfuzz, elasticsearch ou llm")
parser.add_argument("--local_base_dados", type=str, required=True, help="define de qual local é a base de dados, ex: Diadema")

parser.add_argument("--arquivo_entrada", type=str, required=True, help="arquivo de entrada com endereços a ser geocodificados")
parser.add_argument("--arquivo_base_cnefe", type=str, required=True, help="arquivo com os endereços do cnefe")

parser.add_argument("--separador_arq_entrada", type=str, required=True, help="separador do arquivo de entrada")
parser.add_argument("--separador_arq_cnefe", type=str, required=True, help="separador do arquivo do cnefe")

parser.add_argument("--colunas_logradouro_entrada", nargs="+", help="coluna de endereço do arquivo de entrada")
parser.add_argument("--colunas_logradouro_cnefe", nargs="+", help="coluna de endereço do arquivo do cnefe")

parser.add_argument("--coluna_bairro_entrada", type=str, required=True, help="coluna de bairro do arquivo de entrada")
parser.add_argument("--coluna_bairro_cnefe", type=str, required=True, help="coluna de bairro do arquivo do cnefe")

parser.add_argument("--coluna_numero_entrada", type=str, required=True, help="coluna de numero do arquivo de entrada")
parser.add_argument("--coluna_numero_cnefe", type=str, required=True, help="coluna de numero do arquivo do cnefe")

parser.add_argument("--coluna_latitude_verdadeira", type=str, required=True, help="coluna com a latitude verdadeira do arquivo de entrada")
parser.add_argument("--coluna_longitude_verdadeira", type=str, required=True, help="coluna com a longitude verdadeira do arquivo de entrada")
parser.add_argument("--coluna_cd_setor_verdadeira", type=str, required=True, help="coluna com o setor verdadeiro do arquivo de entrada")

parser.add_argument("--coluna_latitude_resultante", type=str, required=True, help="coluna com a latitude verdadeira do arquivo do cnefe")
parser.add_argument("--coluna_longitude_resultante", type=str, required=True, help="coluna com a longitude verdadeira do arquivo do cnefe")
parser.add_argument("--coluna_cd_setor_resultante", type=str, required=True, help="coluna com o setor verdadeiro do arquivo do cnefe")

parser.add_argument("--cod_unico_endereco", type=str, required=True, help="codigo unico do endereço do cnefe")


args = parser.parse_args()


# coloca os argumentos nas variaveis

# dados dos arquivos de entrada e do cnefe
arquivo_entrada = args.arquivo_entrada
arquivo_base_cnefe = args.arquivo_base_cnefe

sep_arq_entrada = args.separador_arq_entrada
sep_arq_cnefe = args.separador_arq_cnefe

# colunas
colunas_logradouro_entrada = args.colunas_logradouro_entrada
colunas_logradouro_cnefe = args.colunas_logradouro_cnefe

coluna_bairro_entrada = args.coluna_bairro_entrada
coluna_bairro_cnefe = args.coluna_bairro_cnefe

coluna_numero_entrada = args.coluna_numero_entrada
coluna_numero_cnefe = args.coluna_numero_cnefe

# dados do arquivo de entrada
coluna_latitude_verdadeira = args.coluna_latitude_verdadeira
coluna_longitude_verdadeira = args.coluna_longitude_verdadeira
coluna_cd_setor_verdadeira = args.coluna_cd_setor_verdadeira

# dados do arquivo do cnefe
coluna_latitude_resultante = args.coluna_latitude_resultante
coluna_longitude_resultante = args.coluna_longitude_resultante
coluna_cd_setor_resultante = args.coluna_cd_setor_resultante

cod_unico_endereco = args.cod_unico_endereco # codigo que identifica o endereço no cnefe

base_dados = normalizar(args.local_base_dados) # local da base de dados para colocar no nome do arquivo final


# Parâmetros de comparação
algoritmo = args.algoritmo  # 'rapidfuzz' ou 'llm' ou 'elasticsearch'
top_n = 20
limiar_similaridade = 85
pesos = {
    "logradouro": 0.7,
    "numero": 0.2,
    "bairro": 0.1
}

# -------------------
# Execução
# -------------------

start_time = time.time()

# Carrega dados
df1 = pd.read_csv(arquivo_entrada, sep=sep_arq_entrada, dtype=str)
df2 = pd.read_csv(arquivo_base_cnefe, sep=sep_arq_cnefe, dtype=str)

# Executa a comparação
df_resultados = comparar(
    df1, df2,
    colunas_logradouro1=colunas_logradouro_entrada,
    colunas_logradouro2=colunas_logradouro_cnefe,
    col_bairro1=coluna_bairro_entrada,
    col_bairro2=coluna_bairro_cnefe,
    col_num1=coluna_numero_entrada,
    col_num2=coluna_numero_cnefe,
    algoritmo=algoritmo,
    top_n=top_n,
    limiar_similaridade=limiar_similaridade,
    peso_logradouro=pesos["logradouro"],
    peso_numero=pesos["numero"],
    peso_bairro=pesos["bairro"],
    latitude_verdadeira=coluna_latitude_verdadeira,
    longitude_verdadeira=coluna_longitude_verdadeira,
    cd_setor_verdadeiro=coluna_cd_setor_verdadeira,
    latitude_resultante=coluna_latitude_resultante,
    longitude_resultante=coluna_longitude_resultante,
    cd_setor_resultante=coluna_cd_setor_resultante,
    cod_unico_endereco=cod_unico_endereco
)

# Resumo de similaridade
faixas = {
    "100": (100, 100),
    "91-99": (91, 99),
    "81-90": (81, 90),
    "0-80": (0, 80)
}

contagem_faixas = {
    nome: df_resultados[(df_resultados["similaridade_final"] >= min_val) &
                        (df_resultados["similaridade_final"] <= max_val)].shape[0]
    for nome, (min_val, max_val) in faixas.items()
}

df_resumo = pd.DataFrame(list(contagem_faixas.items()), columns=["Faixa Similaridade", "Quantidade"])

# -------------------
# Exporta CSV
# -------------------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Cria pasta de resultados separada pelo algoritmo
pasta_resultados = os.path.join("results", f"result_{algoritmo}")
os.makedirs(pasta_resultados, exist_ok=True)

# Gera os nomes dos arquivos
arquivo_resultados = os.path.join(pasta_resultados, f"result_{base_dados}_{timestamp}.csv")
arquivo_resumo = os.path.join(pasta_resultados, f"resumo_{base_dados}_{timestamp}.csv")

# Salva CSV
df_resultados.to_csv(arquivo_resultados, index=False, sep=";")
df_resumo.to_csv(arquivo_resumo, index=False, sep=";")
elapsed = time.time() - start_time
print(f"CSV de resultados salvo em: {arquivo_resultados}")
print(f"CSV de resumo salvo em: {arquivo_resumo}")
print(f"Tempo de execução: {elapsed:.2f} segundos.")