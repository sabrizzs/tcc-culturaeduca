# run_normalizacao.py
import pandas as pd
from datetime import datetime, timedelta
from normalizar import normalizar_datasets
import time
import os
import argparse
import unicodedata
import re

"""
Run normalizacao
Responsabilidades:
1. Carregar arquivos de dataset.
2. Normaliza colunas de logradouro, número, bairro e codigo_setor.
4. Salvar o dataset normalizado em csv.
"""

inicio = datetime.now()
print("Início da execução:", inicio.strftime("%Y-%m-%d %H:%M:%S"))

# normaliza o paramentro de dataset local_base_dados
def normalizar(texto: str) -> str:
    # remove acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    # tudo minúsculo
    texto = texto.lower()
    # troca qualquer sequência de espaços por underline
    texto = re.sub(r'\s+', '_', texto)
    return texto


# -------------------
# Configurações do usuário - dados do dataset
# -------------------

parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

parser.add_argument("--tipo_dados", type=str, required=True, help="se é entrada ou do cnefe")
parser.add_argument("--local_base_dados", type=str, required=True, help="define do qual local é a base de dados, ex: Diadema")

parser.add_argument("--arquivo_dataset", type=str, required=True, help="arquivo do dataset com endereços a ser geocodificados")

parser.add_argument("--separador_arq_dataset", type=str, required=True, help="separador do arquivo do dataset")

parser.add_argument("--colunas_logradouro_dataset", nargs="+", help="coluna de endereço do arquivo do dataset")

parser.add_argument("--coluna_bairro_dataset", type=str, required=True, help="coluna de bairro do arquivo do dataset")

parser.add_argument("--coluna_numero_dataset", type=str, required=True, help="coluna de numero do arquivo do dataset")

parser.add_argument("--coluna_cd_setor_dataset", type=str, required=True, help="coluna com o setor censitario do arquivo do dataset")

args = parser.parse_args()

# -------------------
# Coloca os argumentos nas variaveis
# -------------------

# dados dos arquivos de dataset e do cnefe
arquivo_dataset = args.arquivo_dataset

sep_arq_dataset = args.separador_arq_dataset

# colunas
colunas_logradouro_dataset = args.colunas_logradouro_dataset

coluna_bairro_dataset = args.coluna_bairro_dataset

coluna_numero_dataset = args.coluna_numero_dataset

# dados do arquivo de dataset
coluna_cd_setor_dataset = args.coluna_cd_setor_dataset

# variaveis para nome de arquivos finais
base_dados = normalizar(args.local_base_dados) # local da base de dados para colocar no nome do arquivo final
tipo_dados = normalizar(args.tipo_dados) # entrada ou cnefe

# -------------------
# Execução
# -------------------

start_time = time.time()

# Carrega dados
df = pd.read_csv(arquivo_dataset, sep=sep_arq_dataset, dtype=str)

# Executa a comparação
df_dataset_normalizado = normalizar_datasets(
    df,
    colunas_logradouro=colunas_logradouro_dataset,
    col_bairro=coluna_bairro_dataset,
    col_num=coluna_numero_dataset,
    cd_setor=coluna_cd_setor_dataset
)

# -------------------
# Exporta CSV
# -------------------

# Cria pasta de resultados separada pelo algoritmo
pasta_resultados = "datasets_normalizados"
os.makedirs(pasta_resultados, exist_ok=True)

# Gera os nomes dos arquivos
arquivo_dataset_normalizada = os.path.join(pasta_resultados, f"normalizado_{base_dados}_{tipo_dados}.csv")

# Salva CSV
df_dataset_normalizado.to_csv(arquivo_dataset_normalizada, index=False, sep=";") # ; será o separador dos arquivos normalizados

elapsed = time.time() - start_time
print(f"CSV do dataset normalizado salvo em: {arquivo_dataset_normalizada}")
print("Tempo de execução:", str(timedelta(seconds=int(elapsed))))