import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scipy.stats import gaussian_kde


# ============================================================
# 1) CONFIGURAÇÃO GERAL DAS CIDADES E ARQUIVOS
# ============================================================

CIDADES = {
    "Diadema": {
        "arquivos": {
            "RapidFuzz": "resultado_final_diadema_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_diadema_elasticsearch.csv",
            # "LLM": ,
            #"GeoCodeBR": ,
        },
        "setores": {
            "RapidFuzz": {"match": 28, "mismatch": 13},
            "ElasticSearch": {"match": 28, "mismatch": 13},
            # "LLM": {"match": X, "mismatch": Y},
            #"GeoCodeBR": {"match": X, "mismatch": Y},
        }
    },

    "Rondônia": {
        "arquivos": {
            "RapidFuzz": "resultado_final_rondonia_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_rondonia_elasticsearch.csv",
            # "LLM": ,
            "GeoCodeBR": "resultado_final_geocodebr_ro.csv",
        },
        "setores": {
            "RapidFuzz": {"match": 193, "mismatch": 1050},
            "ElasticSearch": {"match": 494, "mismatch": 749},
            # "LLM": {"match": X, "mismatch": Y},
            "GeoCodeBR": {"match": 306, "mismatch": 937},
        }
    },

    "São Paulo": {
        "arquivos": {
            "RapidFuzz": "resultado_final_sao_paulo_rapidfuzz.csv",
            "ElasticSearch": "resultado_final_sao_paulo_elasticsearch.csv",
            # "LLM": ,
            "GeoCodeBR": "resultado_final_geocodebr_mun_sp.csv",
        },
        "setores": {
            "RapidFuzz": {"match": 1699, "mismatch": 5605},
            "ElasticSearch": {"match": 2078, "mismatch": 5226},
            # "LLM": {"match": X, "mismatch": Y},
            "GeoCodeBR": {"match": 315, "mismatch": 6986},
        }
    }
}



# ============================================================
# 2) FUNÇÃO DO GRÁFICO DE ROSCA (MATCH/MISMATCH)
# ============================================================

def grafico_roscas_setores(nome_cidade, comparacao_setores, output_dir):

    algoritmos = list(comparacao_setores.keys())

    fig, axes = plt.subplots(1, len(algoritmos), figsize=(14, 6))

    for ax, alg in zip(axes, algoritmos):

        valores = [
            comparacao_setores[alg]["match"],
            comparacao_setores[alg]["mismatch"]
        ]
        labels = ["Match", "Mismatch"]
        cores = ["#4CAF50", "#F44336"]

        ax.pie(
            valores,
            labels=labels,
            colors=cores,
            autopct='%1.1f%%',
            pctdistance=0.8,
            labeldistance=1.1,
            wedgeprops={'width':0.35, 'edgecolor':'white'}
        )

        ax.set_title(alg)

    plt.suptitle(f"Percentual de Pontos no Setor Censitário Correto - {nome_cidade}", fontsize=15)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/setores_rosca.png", dpi=300)
    plt.close()

# =====================================================================
# 3) GRÁFICO DE DISTÂNCIA ENTRE PONTOS — KDE (DENSIDADE)
# =====================================================================
def grafico_kde(df_all, nome_cidade, output_dir):

    # ---------------------------------------------------------
    # LIMPEZA dos valores de desvio antes de gerar o KDE
    # Remove NaN, inf e valores negativos
    # ---------------------------------------------------------
    df_all = df_all.copy()
    df_all = df_all[np.isfinite(df_all["desvio_metros"])]
    df_all = df_all[df_all["desvio_metros"] >= 0]

    plt.figure(figsize=(10,6))

    sns.kdeplot(
        data=df_all,
        x="desvio_metros",
        hue="alg",
        clip=(0, None),       # corta abaixo de zero
        linewidth=2
    )

    plt.title(f"Distribuição do Erro de Distância (Real vs. Encontrado) - {nome_cidade}")
    plt.xlabel("Erro de Distância (m)")
    plt.ylabel("Densidade de Ocorrências")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/distancia_kde.png", dpi=300)
    plt.close()

# ============================================================
# 4) EXECUÇÃO AUTOMÁTICA PARA TODAS AS CIDADES
# ============================================================

if __name__ == "__main__":

    for cidade, info in CIDADES.items():

        print(f"\n📍 Gerando gráficos para {cidade}...")

        output_dir = f"graficos_{cidade.lower().replace(' ', '_')}"
        os.makedirs(output_dir, exist_ok=True)

        # carregar todos os CSVs da cidade
        dfs = []
        for alg, arq in info["arquivos"].items():
            if not os.path.exists(arq):
                print(f"⚠ Arquivo não encontrado: {arq} (pulando)")
                continue

            df = pd.read_csv(arq)
            df["alg"] = alg
            dfs.append(df)

        df_all = pd.concat(dfs)

        # gerar gráficos
        grafico_roscas_setores(cidade, info["setores"], output_dir)
        grafico_kde(df_all, cidade, output_dir)

        print(f"✔ Gráficos prontos em: {output_dir}/")
