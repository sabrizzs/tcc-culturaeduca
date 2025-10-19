# run_comparador.py
import pandas as pd
from datetime import datetime
from comparador import comparar, try_int
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
# Configurações do usuário
# -------------------

# Arquivos de entrada
arquivo1 = "cnes_geo_padrao_ouro_diadema.csv"
arquivo2 = "3513801_DIADEMA.csv"

# Colunas
colunas_logradouro_arquivo1 = ["NO_LOGRADO"]
colunas_logradouro_arquivo2 = ["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR"]

coluna_bairro_arquivo1 = "NO_BAIRRO"
coluna_bairro_arquivo2 = "DSC_LOCALIDADE"

coluna_numero_arquivo1 = "NU_ENDEREC"
coluna_numero_arquivo2 = "NUM_ENDERECO"

# Parâmetros de comparação
algoritmo = "llm"  # 'rapidfuzz' ou 'llm' ou 'elasticsearch'
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
df1 = pd.read_csv(arquivo1, sep=";", dtype=str)
df2 = pd.read_csv(arquivo2, sep=";", dtype=str)

# Converte números para inteiro
df1["numero_logradouro"] = df1[coluna_numero_arquivo1].apply(try_int)
df2["numero_logradouro"] = df2[coluna_numero_arquivo2].apply(try_int)

# Executa a comparação
df_resultados = comparar(
    df1, df2,
    colunas_logradouro1=colunas_logradouro_arquivo1,
    colunas_logradouro2=colunas_logradouro_arquivo2,
    col_bairro1=coluna_bairro_arquivo1,
    col_bairro2=coluna_bairro_arquivo2,
    col_num1="numero_logradouro",
    col_num2="numero_logradouro",
    algoritmo=algoritmo,
    top_n=top_n,
    limiar_similaridade=limiar_similaridade,
    peso_logradouro=pesos["logradouro"],
    peso_numero=pesos["numero"],
    peso_bairro=pesos["bairro"]
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

# Exporta Excel
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
nome_arquivo = f"result_{timestamp}.xlsx"

# Cria pasta de resultados separada pelo algoritmo
pasta_resultados = os.path.join("results", f"result_{algoritmo}")
os.makedirs(pasta_resultados, exist_ok=True)

# Define o caminho completo do arquivo
caminho_arquivo = os.path.join(pasta_resultados, nome_arquivo)

with pd.ExcelWriter(caminho_arquivo, engine="xlsxwriter") as writer:
    df_resultados.to_excel(writer, sheet_name="Enderecos", index=False)
    df_resumo.to_excel(writer, sheet_name="Resumo similaridade", index=False)

elapsed = time.time() - start_time
print(f"Comparação concluída e arquivo salvo em {caminho_arquivo}.")
print(f"Tempo de execução: {elapsed:.2f} segundos.")
