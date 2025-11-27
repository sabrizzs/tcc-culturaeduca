import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scipy.stats import gaussian_kde


# ============================================================
# 1) CONFIGURAÇÃO GERAL — APENAS CAMINHOS DOS ARQUIVOS
# ============================================================

CIDADES = {
    "Diadema": {
        "arquivos": {
            "RapidFuzz": "resultado_final_diadema_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_diadema_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_diadema_geocodebr.csv",
            # "LLM": "",
        }
    },

    "Rondônia": {
        "arquivos": {
            "RapidFuzz": "resultado_final_rondonia_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_rondonia_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_geocodebr_ro.csv",
            # "LLM": "",
        }
    },

    "São Paulo": {
        "arquivos": {
            "RapidFuzz": "resultado_final_sao_paulo_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_sao_paulo_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_geocodebr_mun_sp.csv",
            # "LLM": "",
        }
    }
}



# ============================================================
# 2) FUNÇÕES DE CLASSIFICAÇÃO AUTOMÁTICA
# ============================================================

def classificar_setor(row):
    if row["setor_correspondente"] is True:
        return "Correto"
    elif row["setor_vizinho_verdadeiro"] is True:
        return "Vizinho"
    else:
        return "Errado"


def contar_categoria(df):
    df = df.copy()
    df["categoria_setor"] = df.apply(classificar_setor, axis=1)
    return df["categoria_setor"].value_counts().to_dict()


def contar_match_mismatch(df):
    categorias = contar_categoria(df)
    return {
        "match": categorias.get("Correto", 0),
        "mismatch": categorias.get("Vizinho", 0) + categorias.get("Errado", 0)
    }



# ============================================================
# 3) GRÁFICO DE ROSCA — MATCH / MISMATCH
# ============================================================

def grafico_rosca_match(df_por_algoritmo, nome_cidade, output_dir):

    fig, axes = plt.subplots(1, len(df_por_algoritmo), figsize=(14, 6))

    if len(df_por_algoritmo) == 1:
        axes = [axes]

    for ax, (alg, df) in zip(axes, df_por_algoritmo.items()):
        cont = contar_match_mismatch(df)

        valores = [cont["match"], cont["mismatch"]]
        labels = ["Match", "Mismatch"]
        cores  = ["#4CAF50", "#F44336"]

        ax.pie(
            valores,
            labels=labels,
            colors=cores,
            autopct='%1.1f%%',
            pctdistance=0.8,
            labeldistance=1.1,
            wedgeprops={'width': 0.35, 'edgecolor': 'white'}
        )

        ax.set_title(alg)

    plt.suptitle(f"Percentual de pontos no setor censitário correto — {nome_cidade}", fontsize=15)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/rosca_match.png", dpi=300)
    plt.close()



# ============================================================
# 4) GRÁFICO DE ROSCA — CORRETO / VIZINHO / ERRADO
# ============================================================

def grafico_rosca_categorias(df_por_algoritmo, nome_cidade, output_dir):

    fig, axes = plt.subplots(1, len(df_por_algoritmo), figsize=(16, 6))

    if len(df_por_algoritmo) == 1:
        axes = [axes]

    cores = {
        "Correto": "#4CAF50",
        "Vizinho": "#FF9800",
        "Errado":  "#F44336",
    }

    for ax, (alg, df) in zip(axes, df_por_algoritmo.items()):
        categorias = contar_categoria(df)

        labels = ["Correto", "Vizinho", "Errado"]
        valores = [categorias.get(k, 0) for k in labels]

        ax.pie(
            valores,
            labels=labels,
            colors=[cores[k] for k in labels],
            autopct='%1.1f%%',
            pctdistance=0.8,
            labeldistance=1.1,
            wedgeprops={'width': 0.35, 'edgecolor': 'white'}
        )

        ax.set_title(alg)

    plt.suptitle(f"Percentual de pontos no setor censitário correto — {nome_cidade}", fontsize=16)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/rosca_categorias.png", dpi=300)
    plt.close()



# ============================================================
# 5) GRÁFICO KDE — DISTRIBUIÇÃO DO ERRO DE DISTÂNCIA
# ============================================================

def grafico_kde(df_all, nome_cidade, output_dir):

    df_all = df_all.copy()
    df_all = df_all[np.isfinite(df_all["desvio_metros"])]
    df_all = df_all[df_all["desvio_metros"] >= 0]

    plt.figure(figsize=(10, 6))

    sns.kdeplot(
        data=df_all,
        x="desvio_metros",
        hue="alg",
        clip=(0, None),
        linewidth=2
    )

    plt.title(f"Distribuição do erro de distância (real vs encontrado) — {nome_cidade}")
    plt.xlabel("Erro de distância (m)")
    plt.ylabel("Densidade de ocorrências")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/kde_distancia.png", dpi=300)
    plt.close()



# ============================================================
# 6) EXECUÇÃO AUTOMÁTICA PARA TODAS AS CIDADES
# ============================================================

if __name__ == "__main__":

    for cidade, info in CIDADES.items():

        print(f"\n📍 Gerando gráficos para {cidade}...")

        output_dir = f"graficos_{cidade.lower().replace(' ', '_')}"
        os.makedirs(output_dir, exist_ok=True)

        dfs_algoritmos = {}

        for alg, arq in info["arquivos"].items():

            if not os.path.exists(arq):
                print(f"⚠ Arquivo não encontrado: {arq} — pulando")
                continue

            df = pd.read_csv(arq)
            df["alg"] = alg
            dfs_algoritmos[alg] = df

        # Concatenado geral para o KDE
        df_all = pd.concat(dfs_algoritmos.values())

        # Gráficos
        grafico_rosca_match(dfs_algoritmos, cidade, output_dir)
        grafico_rosca_categorias(dfs_algoritmos, cidade, output_dir)
        grafico_kde(df_all, cidade, output_dir)

        print(f"✔ Gráficos prontos em: {output_dir}/")
