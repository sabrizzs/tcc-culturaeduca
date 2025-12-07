import pandas as pd
import sys

def carregar_csv(caminho_csv: str) -> pd.DataFrame:
    """
    Lê o arquivo CSV e devolve um DataFrame.
    Ajuste o separador (sep) se o seu arquivo usar ';' em vez de ','.
    """
    df = pd.read_csv(caminho_csv)
    return df

def converter_para_bool(serie: pd.Series) -> pd.Series:
    """
    Converte uma coluna com 'True'/'False' (string) para bool.
    Mantém outros valores (como NaN) como estão.
    """
    return serie.map(
        lambda x: True if str(x).strip().lower() == "true"
        else False if str(x).strip().lower() == "false"
        else pd.NA
    )

def analisar_setores(df: pd.DataFrame) -> None:
    # Garante que as colunas existem
    col_corresp = "setor_correspondente"
    col_vizinho = "setor_vizinho_verdadeiro"

    if col_corresp not in df.columns or col_vizinho not in df.columns:
        print("Erro: colunas 'setor_correspondente' e/ou 'setor_vizinho_verdadeiro' não existem no CSV.")
        print("Colunas encontradas:", list(df.columns))
        return

    # Converte strings "True"/"False" para booleanos (opcional mas ajuda)
    df[col_corresp] = converter_para_bool(df[col_corresp])
    df[col_vizinho] = converter_para_bool(df[col_vizinho])

    print("===== Contagem por coluna =====")
    print("\nColuna: setor_correspondente")
    print(df[col_corresp].value_counts(dropna=False))

    print("\nColuna: setor_vizinho_verdadeiro")
    print(df[col_vizinho].value_counts(dropna=False))

    # Tabela cruzada (combinações)
    print("\n===== Combinações (setor_correspondente x setor_vizinho_verdadeiro) =====")
    crosstab = pd.crosstab(df[col_corresp], df[col_vizinho], dropna=False)
    print(crosstab)

    # Se quiser o total de linhas válidas (sem NA nas duas colunas)
    linhas_validas = df[[col_corresp, col_vizinho]].dropna().shape[0]
    print(f"\nLinhas válidas (sem NA nas duas colunas): {linhas_validas}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analisar_setores.py caminho/para/arquivo.csv")
        sys.exit(1)

    caminho = sys.argv[1]
    df = carregar_csv(caminho)
    analisar_setores(df)
