import pandas as pd
from datetime import datetime
from comparador import comparar_enderecos
import time

"""
Script principal para comparar endereços de duas bases de dados usando a função
comparar_enderecos (do código comparador.py).

Passos executados pelo script:
    1. Define os arquivos de entrada:
        * arquivo1 = base de endereços a localizar.
        * arquivo2 = base de referência onde procurar correspondências.
    2. Define quais colunas de cada arquivo compõem o endereço.
    3. Extrai e converte a coluna de número do logradouro em inteiro (quando possível).
    4. Executa a comparação chamando comparar_enderecos:
        - Usa pesos para texto (0.9) e número (0.1).
        - Define o limite mínimo de similaridade (85).
        - Retorna também as Top N sugestões de matches (20).
    5. Faz uma contagem dos resultados agrupados em faixas de similaridade:
        * 100
        * 91–99
        * 81–90
        * 0–80
    6. Gera um arquivo de saída Excel contendo:
        - Aba "Enderecos": matches detalhados.
        - Aba "Resumo similaridade": distribuição por faixa.
"""

start_time = time.time()

# Arquivos e colunas
arquivo1 = "cnes_geo_padrao_ouro_diadema.csv" # endereços a serem localizados na base de referência
arquivo2 = "3513801_DIADEMA.csv" # base de referência onde o algoritmo vai tentar encontrar correspondências

# Colunas do logradouro
colunas_logradouro_arquivo1 = ["NO_LOGRADO"]
colunas_logradouro_arquivo2 = ["NOM_TIPO_SEGLOGR", "NOM_TITULO_SEGLOGR", "NOM_SEGLOGR"]

# Colunas do bairro
coluna_bairro_arquivo1 = "NO_BAIRRO"
coluna_bairro_arquivo2 = "DSC_LOCALIDADE"

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
    colunas_logradouro1=colunas_logradouro_arquivo1,
    colunas_logradouro2=colunas_logradouro_arquivo2,
    col_bairro1=coluna_bairro_arquivo1,
    col_bairro2=coluna_bairro_arquivo2,
    col_num1="numero_logradouro",
    col_num2="numero_logradouro",
    limiar_similaridade=85,
    peso_logradouro=0.7,  # peso maior para rua
    peso_numero=0.2,      # número também importante
    peso_bairro=0.1,      # bairro como refinamento
    top_n=20
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


