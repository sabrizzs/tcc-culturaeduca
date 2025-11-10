# geocode_csv_with_geocodebr.py
# -*- coding: utf-8 -*-
# TESTAR ESSE CODIGO
import os
import math
import pandas as pd

# --- rpy2 (ponte Python -> R) ---
from rpy2 import robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects.conversion import localconverter
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter


# Ativa conversão automática R <-> pandas
# pandas2ri.activate()



# --- Setup R/CRAN e instalação garantida do geocodeBR ---
from rpy2 import robjects as ro
from rpy2.robjects.packages import importr
from rpy2.rinterface_lib.embedded import RRuntimeError

def ensure_pkg_geocodeBR():
    # Repositório e lib do usuário (gravável)
    ro.r('options(repos = c(CRAN = "https://cloud.r-project.org"))')
    ro.r('dir.create(Sys.getenv("R_LIBS_USER"), showWarnings = FALSE, recursive = TRUE)')
    ro.r('.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))')

    # 1) tenta carregar (nome correto, com BR maiúsculo)
    try:
        return importr("geocodeBR")
    except RRuntimeError:
        pass

    # 2) tenta instalar do CRAN (se disponível)
    try:
        utils = importr("utils")
        utils.install_packages("geocodeBR")
        return importr("geocodeBR")
    except RRuntimeError:
        pass

    # 3) fallback: instala do GitHub (ipeaGIT/geocodeBR)
    try:
        utils = importr("utils")
        ro.r('if (!requireNamespace("remotes", quietly=TRUE)) install.packages("remotes")')
        ro.r('remotes::install_github("ipeaGIT/geocodeBR")')
        return importr("geocodeBR")
    except RRuntimeError as e:
        # Log de diagnóstico útil
        print("R version:", ro.r('R.version.string')[0])
        print(".libPaths():", list(ro.r('.libPaths()')))
        print("requireNamespace(geocodeBR)?", bool(ro.r('requireNamespace("geocodeBR", quietly=TRUE)')))
        raise
print('PASSOU POR AQUI 0')
geocodeBR = ensure_pkg_geocodeBR()




print('PASSOU POR AQUI 1')

# Carrega o pacote R geocodebr (certifique-se de tê-lo instalado no R)
ro.r('library(geocodebr)')

print('PASSOU POR AQUI 2')

# Referência à função R geocode()
geocode_r = ro.r['geocode']

def geocode_csv_with_geocodebr(
    input_csv: str,
    output_csv: str,
    sep: str = ",",
    encoding: str = "utf-8",
    # mapeie aqui suas colunas do CSV -> nomes esperados pelo geocodebr
    column_map: dict = None,
    # processa em lotes para evitar travar tudo de uma vez (ajuste conforme a máquina)
    batch_size: int = 2000
):
    """
    Lê um CSV, prepara colunas para o geocodebr e salva um CSV com lat/lon.
    column_map: mapeamento de nomes do seu CSV para os nomes esperados pelo geocodebr:
        {
          "logradouro": "logradouro_normalizado",
          "numero":     "numero_int",
          "bairro":     "bairro_normalizado",
          "municipio":  "municipio_normalizado",   
          "uf":         "sigla_uf_normalizado" 
        }
    """
    if column_map is None:
        # AJUSTE AQUI para o seu CSV!
        column_map = {
            "logradouro": "logradouro_normalizado",
            "numero":     "numero_int",
            "bairro":     "bairro_normalizado",
            "municipio":  "municipio_normalizado",   # <-- troque para o nome real no seu CSV
            "uf":         "sigla_uf_normalizado"           # <-- troque para o nome real no seu CSV
        }

    # 1) Lê o CSV
    df = pd.read_csv(input_csv, sep=sep, dtype=str, encoding=encoding)
    # Garante que as colunas existam
    missing = [src for src in column_map.values() if src not in df.columns]
    if missing:
        raise ValueError(f"As colunas faltando no CSV: {missing}. "
                         f"Ajuste 'column_map' para corresponder ao seu arquivo.")

    # 2) Seleciona/renomeia para o padrão do geocodebr
    df_geo = df[list(column_map.values())].copy()
    df_geo.columns = list(column_map.keys())  # vira: logradouro, numero, bairro, municipio, uf

    # Opcional: limpeza simples
    # for c in ["logradouro", "numero", "bairro", "municipio", "uf"]:
    #     if c in df_geo:
    #         df_geo[c] = df_geo[c].fillna("").astype(str).str.strip()

    # 3) Geocodifica em batches
    results = []
    n = len(df_geo)
    n_batches = math.ceil(n / batch_size)

    for i in range(n_batches):
        start = i * batch_size
        end = min((i + 1) * batch_size, n)
        chunk = df_geo.iloc[start:end].copy()

        # Converte pandas -> data.frame do R e chama geocode()
        with localconverter(ro.default_converter + pandas2ri.converter):
            r_df = pandas2ri.py2rpy(chunk)

        r_out = geocode_r(r_df)  # chama geocodebr::geocode()

        # Converte de volta para pandas
        with localconverter(ro.default_converter + pandas2ri.converter):
            pd_out = pandas2ri.rpy2py(r_out)

        # Normaliza nomes (o geocodebr costuma devolver longitude/latitude)
        # Ajuste abaixo se o pacote devolver colunas com nomes diferentes:
        # exemplo comum: ['longitude','latitude','score','situacao', ...]
        expected_lat = None
        expected_lon = None
        for col in pd_out.columns:
            if col.lower() == "latitude":
                expected_lat = col
            if col.lower() == "longitude":
                expected_lon = col

        if not expected_lat or not expected_lon:
            # Ajuda de debug se mudar em versões futuras
            raise RuntimeError(
                "Não encontrei colunas 'latitude'/'longitude' no retorno do geocodebr. "
                f"Colunas recebidas: {list(pd_out.columns)}"
            )

        # Guarda o resultado desse lote mantendo o índice original
        pd_out.index = chunk.index
        results.append(pd_out[[expected_lon, expected_lat]])

        print(f"Lote {i+1}/{n_batches} geocodificado: linhas {start}:{end}")

    # 4) Junta todos os lotes e anexa ao dataframe original
    df_coords = pd.concat(results).sort_index()
    df_final = df.copy()
    df_final["longitude"] = df_coords.iloc[:, 0]
    df_final["latitude"]  = df_coords.iloc[:, 1]

    # 5) Salva CSV final
    df_final.to_csv(output_csv, index=False, sep=sep, encoding=encoding)
    print(f"Arquivo gerado: {output_csv}")

if __name__ == "__main__":
    # EXEMPLO DE USO:
    # Ajuste os caminhos e o mapeamento de colunas para o seu arquivo.
    geocode_csv_with_geocodebr(
        input_csv="entradas.csv",          # seu arquivo de entrada
        output_csv="saidas_geocod.csv",    # arquivo de saída com lat/lon
        sep=";",                           # se seu CSV usa ; como separador
        column_map = {
            "logradouro": "logradouro_normalizado",
            "numero":     "numero_int",
            "bairro":     "bairro_normalizado",
            "municipio":  "municipio_normalizado",   # <-- troque para o nome real no seu CSV
            "uf":         "sigla_uf_normalizado"           # <-- troque para o nome real no seu CSV
        },
        batch_size=2000
    )
