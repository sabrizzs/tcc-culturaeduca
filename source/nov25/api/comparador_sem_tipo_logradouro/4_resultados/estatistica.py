# import pandas as pd
# import numpy as np

# # df= pd.read_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/results/result_geocodebr/result_geocodebr_mun_sp_com_desvio.csv", sep=";", dtype=str)
# df= pd.read_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/comparador_sem_tipo_logradouro/3_geocodificacao/results/result_rapidfuzz/resultado_diadema_com_desempate.csv", sep=",", dtype=str)


# bins = [0, 500, 1000, 2000, 5000, 10000, 20000, 50000, np.inf]
# labels = [
#     "0-500m",
#     "500-1000m",
#     "1000-2000m",
#     "2000-5000m",
#     "5000-10000m",
#     "10000-20000m",
#     "20000-50000m",
#     ">50000m"
# ]

# # força conversão para número, converte erros em NaN
# df["desvio_metros_final_limpo"] = pd.to_numeric(df["desvio_metros"], errors="coerce")

# df["faixa"] = pd.cut(df["desvio_metros_final_limpo"], bins=bins, labels=labels, right=False)

# tabela_faixas = df["faixa"].value_counts().sort_index()

# # total de registros válidos
# total = df["desvio_metros"].notna().sum()

# # transforma a contagem em DataFrame
# tabela_faixas_df = tabela_faixas.reset_index()
# tabela_faixas_df.columns = ["faixa_metros", "quantidade"]

# # adiciona percentual
# tabela_faixas_df["percentual"] = (tabela_faixas_df["quantidade"] / total * 100).round(2)

# print(tabela_faixas_df)

import pandas as pd
import numpy as np

# df= pd.read_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/results/result_geocodebr/result_geocodebr_mun_sp_com_desvio.csv", sep=";", dtype=str)
df= pd.read_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/comparador_sem_tipo_logradouro/3_geocodificacao/results/result_elasticsearch/result_rondonia_20251126_010816_com_desvio.csv", sep=";", dtype=str)

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
df["desvio_metros_final_limpo"] = pd.to_numeric(df["desvio_metros"], errors="coerce")
df["faixa"] = pd.cut(df["desvio_metros_final_limpo"], bins=bins, labels=labels, right=False)

tabela_faixas = df["faixa"].value_counts().sort_index()

# total de registros válidos
total = df["desvio_metros"].notna().sum()

# transforma a contagem em DataFrame
tabela_faixas_df = tabela_faixas.reset_index()
tabela_faixas_df.columns = ["faixa_metros", "quantidade"]

# adiciona percentual
tabela_faixas_df["percentual"] = (tabela_faixas_df["quantidade"] / total * 100).round(2)

print("\n===== Distribuição por faixas de desvio =====")
print(tabela_faixas_df)

# ==========================================================
# NOVO: COMPARAÇÃO DOS SETORES
# ==========================================================

# garante que setor seja comparável (string)
df["cd_setor_verdadeiro"] = df["cd_setor_verdadeiro"].astype(str)
df["cd_setor_resultante"] = df["cd_setor_resultante"].astype(str)

# cria coluna indicando match
df["setor_match"] = df["cd_setor_verdadeiro"] == df["cd_setor_resultante"]

# contagens
match_count = df["setor_match"].sum()
mismatch_count = len(df) - match_count

print("\n===== Comparação de Setores =====")
print(f"✔️ Setores iguais (match): {match_count}")
print(f"❌ Setores diferentes (mismatch): {mismatch_count}")

# linhas divergentes
df_mismatch = df[df["setor_match"] == False]

print("\n===== Linhas com setor divergente =====")
print(df_mismatch[["cd_setor_verdadeiro", "cd_setor_resultante", "desvio_metros"]])
