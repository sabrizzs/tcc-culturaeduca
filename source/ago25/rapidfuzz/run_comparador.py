import pandas as pd
from datetime import datetime
from comparador import comparar_enderecos
import time

start_time = time.time()

# Arquivos e colunas
arquivo1 = "cnes_geo_padrao_ouro_diadema.csv"
arquivo2 = "3513801_DIADEMA.csv"

colunas_arquivo1 = ["NO_LOGRADO", "NO_BAIRRO"]
colunas_arquivo2 = ["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR", "DSC_LOCALIDADE"]

# Colunas do número do logradouro para cada arquivo
coluna_numero_arquivo1 = "NU_ENDEREC"
coluna_numero_arquivo2 = "NUM_ENDERECO"

# Carrega dados
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

df1["numero_logradouro"] = extrair_numero(df1, coluna_numero_arquivo1)
df2["numero_logradouro"] = extrair_numero(df2, coluna_numero_arquivo2)

# Executa comparação
df_resultados = comparar_enderecos(
    df1, df2,
    colunas1=colunas_arquivo1,
    colunas2=colunas_arquivo2,
    col_num1="numero_logradouro",
    col_num2="numero_logradouro",
    limiar_similaridade=85,
    peso_texto=0.9,     # peso maior para similaridade de texto
    peso_numero=0.1,    # peso menor para número
    top_n=20            # sugestões no relatório
)

# Nomeia o arquivo de saída com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
nome_arquivo = f"result_{timestamp}.csv"

# Exporta CSV
df_resultados.to_csv(nome_arquivo, sep=";", decimal=",", index=False)

end_time = time.time()
elapsed = end_time - start_time
print(f"Comparação concluída e arquivo salvo em {nome_arquivo}.")
print(f"Tempo de execução: {elapsed:.2f} segundos.")
