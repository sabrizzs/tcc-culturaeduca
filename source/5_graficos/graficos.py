import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scipy.stats import gaussian_kde

# ---------------
# Configuração
# ---------------

CIDADES = {
    "Diadema": {
        "arquivos": {
            "RapidFuzz": "resultado_final_diadema_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_diadema_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_diadema_geocodebr.csv",
            "LLM": "resultado_final_diadema_llm.csv",
        }
    },

    "Rondônia": {
        "arquivos": {
            "RapidFuzz": "resultado_final_rondonia_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_rondonia_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_rondonia_geocodebr.csv",
            "LLM": "resultado_final_rondonia_llm.csv",
        }
    },

    "São Paulo": {
        "arquivos": {
            "RapidFuzz": "resultado_final_sp_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_sp_elasticsearch.csv",
            "GeoCodeBR": "resultado_final_sp_geocodebr.csv",
            # "LLM": "",
        }
    }
}


# ---------------
# Classificação
# ---------------

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

# ---------------
# Gráfico de rosca - correto/vizinho/errado
# ---------------

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

        wedges, texts, autotexts = ax.pie(
            valores,
            colors=[cores[k] for k in labels],
            autopct='%1.1f%%',
            pctdistance=0.8,
            labeldistance=1.1,
            wedgeprops={'width': 0.35, 'edgecolor': 'white'}
        )

        for t in autotexts:
            t.set_fontsize(18)
            t.set_weight("bold")

        ax.set_title(alg, fontsize=19, pad=-40)

    plt.suptitle(
        f"Percentual de pontos no setor censitário correto — {nome_cidade}",
        fontsize=23,
        weight="bold"
    )


    from matplotlib.patches import Patch

    legendas = [
        Patch(facecolor=cores["Correto"], label="Correto"),
        Patch(facecolor=cores["Vizinho"], label="Vizinho"),
        Patch(facecolor=cores["Errado"],  label="Errado")
    ]

    fig.legend(
        handles=legendas,
        loc='lower center',
        ncol=3,
        fontsize=20,
        frameon=False,
        bbox_to_anchor=(0.5, 0.08)  
    )

    #plt.tight_layout()
    plt.savefig(f"{output_dir}/rosca_categorias.png", dpi=300)
    plt.close()



# ---------------
# Gráfico KNE - Distribuição do erro de distância
# ---------------

import matplotlib.ticker as mtick

def grafico_kde(df_all, nome_cidade, output_dir):

    df_all = df_all.copy()
    df_all = df_all[np.isfinite(df_all["desvio_metros"])]
    df_all = df_all[df_all["desvio_metros"] >= 0]

    plt.figure(figsize=(10, 6))

    ax = sns.kdeplot(
        data=df_all,
        x="desvio_metros",
        hue="algoritmo",
        linewidth=2.5
    )

    # reescala o eixo Y para 0–1
    ymax = max(line.get_ydata().max() for line in ax.lines)
    for line in ax.lines:
        line.set_ydata(line.get_ydata() / ymax)

    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Densidade relativa (0–1)", fontsize=17)

    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    ax.yaxis.set_major_locator(mtick.MultipleLocator(0.2))
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))

    plt.title(f"Distribuição do erro de distância (real vs encontrado) — {nome_cidade}", fontsize=18, weight="bold")
    plt.xlabel("Erro de distância (m)", fontsize=17)

    plt.savefig(f"{output_dir}/kde_distancia_relativo.png", dpi=300)
    plt.close()


# ============================================================
# Histograma Logarítmico
# ============================================================

def grafico_hist_abs(df_all, nome_cidade, output_dir):
    df = df_all.copy()
    df = df[np.isfinite(df["desvio_metros"])]
    df = df[df["desvio_metros"] >= 0]
    df["desvio_metros"] = df["desvio_metros"].clip(lower=1)

    plt.figure(figsize=(10, 6))

    sns.histplot(
        data=df,
        x="desvio_metros",
        hue="algoritmo",
        element="step",
        stat="count",     
        common_norm=False,
        bins=80           
    )

    plt.title(f"Distribuição absoluta do erro de distância — {nome_cidade}", fontsize=18, weight="bold")
    plt.xlabel("Erro de distância (m)", fontsize=12)
    plt.ylabel("Quantidade de pontos", fontsize=12)

    plt.savefig(f"{output_dir}/hist_abs_distancia.png", dpi=300)
    plt.close()

# ---------------
# Gera gráficos para as cidades
# ---------------

if __name__ == "__main__":

    for cidade, info in CIDADES.items():

        print(f"\n Gerando gráficos para {cidade}...")

        output_dir = f"graficos_{cidade.lower().replace(' ', '_')}"
        os.makedirs(output_dir, exist_ok=True)

        dfs_algoritmos = {}

        for alg, arq in info["arquivos"].items():

            if not os.path.exists(arq):
                print(f"Arquivo não encontrado: {arq} — pulando")
                continue

            df = pd.read_csv(arq)
            df["algoritmo"] = alg
            dfs_algoritmos[alg] = df

        df_all = pd.concat(dfs_algoritmos.values())

        # Gráficos
        grafico_rosca_categorias(dfs_algoritmos, cidade, output_dir)
        grafico_kde(df_all, cidade, output_dir)

        print(f"Gráficos prontos em: {output_dir}/")