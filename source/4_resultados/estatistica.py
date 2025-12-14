import pandas as pd
import numpy as np

df= pd.read_csv("resultado_geocodebr_norm.csv", sep=";", dtype=str)

bins = [0, 500, 1000, 2000, 5000, 10000, 20000, 50000, np.inf]
labels = [
    "0-500m",
    "500-1000m",
    "1000-2000m",
    "2000-5000m",
    "5000-10000m",
    "10000-20000m",
    "20000-50000m",
    ">50000m"
]

# força conversão para número, converte erros em NaN
df["desvio_metros_final_limpo"] = pd.to_numeric(df["desvio_metros_final"], errors="coerce")
df["faixa"] = pd.cut(df["desvio_metros_final_limpo"], bins=bins, labels=labels, right=False)

tabela_faixas = df["faixa"].value_counts().sort_index()

# total de registros válidos
total = df["desvio_metros_final"].notna().sum()

# transforma a contagem em DataFrame
tabela_faixas_df = tabela_faixas.reset_index()
tabela_faixas_df.columns = ["faixa_metros", "quantidade"]

# adiciona percentual
tabela_faixas_df["percentual"] = (tabela_faixas_df["quantidade"] / total * 100).round(2)

print("\n===== Distribuição por faixas de desvio =====")
print(tabela_faixas_df)
