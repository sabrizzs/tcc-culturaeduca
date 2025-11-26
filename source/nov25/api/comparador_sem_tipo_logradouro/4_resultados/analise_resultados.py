import numpy as np
import pandas as pd

# Raio médio da Terra em metros (similar ao usado em ST_DistanceSphere)
R = 6371008.8

def haversine_series(lat1, lon1, lat2, lon2):
    # garante que tudo é numérico (float), valores inválidos viram NaN
    lat1 = pd.to_numeric(lat1, errors="coerce")
    lon1 = pd.to_numeric(lon1, errors="coerce")
    lat2 = pd.to_numeric(lat2, errors="coerce")
    lon2 = pd.to_numeric(lon2, errors="coerce")

    # converte para radianos como numpy arrays
    lat1_rad = np.radians(lat1.to_numpy())
    lon1_rad = np.radians(lon1.to_numpy())
    lat2_rad = np.radians(lat2.to_numpy())
    lon2_rad = np.radians(lon2.to_numpy())

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c  # distância em metros


df_res= pd.read_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/comparador_sem_tipo_logradouro/3_geocodificacao/results/result_elasticsearch/result_rondonia_20251126_011657.csv", sep=";", dtype=str)

# calcula a distância linha a linha (vetorizado, rápido)
df_res["desvio_metros"] = haversine_series(
    df_res["latitude_verdadeira"],
    df_res["longitude_verdadeira"],
    df_res["latitude_resultante"],
    df_res["longitude_resultante"],
)

df_res.to_csv("/home/samantha/tcc-culturaeduca/source/nov25/api/comparador_sem_tipo_logradouro/3_geocodificacao/results/result_elasticsearch/result_rondonia_20251126_011657_com_desvio.csv", index=False, sep=";")
