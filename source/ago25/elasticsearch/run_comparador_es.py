import pandas as pd
from datetime import datetime
import time
import os

# Importa a versão refatorada
from comparador_es import comparar_enderecos_es

start_time = time.time()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
arquivo1 = os.path.join(BASE_DIR, "cnes_geo_padrao_ouro_diadema.csv")
arquivo2 = os.path.join(BASE_DIR, "3513801_DIADEMA.csv")

colunas_arquivo1 = ["NO_LOGRADO"]
colunas_arquivo2 = ["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR"]

# colunas com bairro
coluna_bairro_arquivo1 = "NO_BAIRRO"
coluna_bairro_arquivo2 = "DSC_LOCALIDADE"

# Colunas com número
coluna_numero_arquivo1 = "NU_ENDEREC"
coluna_numero_arquivo2 = "NUM_ENDERECO"

# Leitura dos arquivos
df1 = pd.read_csv(arquivo1, sep=";", dtype=str)
df2 = pd.read_csv(arquivo2, sep=";", dtype=str)

# Função para extrair número como inteiro
def extrair_numero(df, coluna_num):
    def try_int(x):
        try:
            return int(str(x).strip())
        except:
            return None
    return df[coluna_num].apply(try_int)

# Cria coluna auxiliar de número padronizado
df1["numero_logradouro"] = extrair_numero(df1, coluna_numero_arquivo1)
df2["numero_logradouro"] = extrair_numero(df2, coluna_numero_arquivo2)


# Executa a comparação usando Elasticsearch
df_resultados = comparar_enderecos_es(
    df1, df2,
    colunas1=colunas_arquivo1,
    colunas2=colunas_arquivo2,
    coluna_bairro_arquivo1=coluna_bairro_arquivo1,
    coluna_bairro_arquivo2=coluna_bairro_arquivo2,
    col_num1="numero_logradouro",
    col_num2="numero_logradouro",
    peso_texto=0.9,
    peso_numero=0.1,
    top_n=20,
    index_name="enderecos_ref_diadema"  # índice único para este job
)

# Contagem por faixas de similaridade para análise
faixas = {
    "100": (100, 100),
    "91-99": (91, 99),
    "81-90": (81, 90),
    "0-80": (0, 80)
}

contagem_faixas = {}
for nome, (min_val, max_val) in faixas.items():
    contagem = df_resultados[
        (df_resultados["similaridade_final"] >= min_val) &
        (df_resultados["similaridade_final"] <= max_val)
    ].shape[0]
    contagem_faixas[nome] = contagem

df_resumo = pd.DataFrame(list(contagem_faixas.items()), columns=["Faixa Similaridade", "Quantidade"])


# Nomeia o arquivo de saída com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
nome_arquivo = f"result_{timestamp}.xlsx"

# Exporta CSV
with pd.ExcelWriter(nome_arquivo, engine="xlsxwriter") as writer:
    df_resultados.to_excel(writer, sheet_name="Enderecos", index=False)
    df_resumo.to_excel(writer, sheet_name="Resumo similaridade", index=False)

# Contagem de tempo de execução
end_time = time.time()
elapsed = end_time - start_time
print(f"Comparação concluída e arquivo salvo em {nome_arquivo}.")
print(f"Tempo de execução: {elapsed:.2f} segundos.")
