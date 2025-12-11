import pandas as pd

# Configurações

# Arquivo gabarito 
CAMINHO_GABARITO = "results/result_rapidfuzz/result_20251012_142504_analisado_gabarito.xlsx"

CAMINHO_RESULTADO_NOVO = r"results\result_llm\result_20251125_115213.xlsx"  # <<< troque aqui

SHEET_RESULTADO_NOVO = "Enderecos"

# Arquivo de saída com o relatório de validação
CAMINHO_RELATORIO = "relatorio_validacao_gabarito.xlsx"


# Carrega dados

print("Carregando gabarito...")
df_gab = pd.read_excel(CAMINHO_GABARITO) 

print("Carregando resultado novo...")
df_novo = pd.read_excel(CAMINHO_RESULTADO_NOVO, sheet_name=SHEET_RESULTADO_NOVO)

# Verifica se idx_df1 é único no gabarito (esperado)
if not df_gab["idx_df1"].is_unique:
    raise ValueError("idx_df1 não é único no gabarito.")

# Sufixos diferentes para distinguir colunas
df_merge = df_gab.merge(
    df_novo,
    on="idx_df1",
    how="left",
    suffixes=("_gab", "_novo")
)

# Se algum idx_df1 do gabarito não existir no resultado novo, vai ficar NaN em idx_df2_novo
faltando = df_merge["idx_df2_novo"].isna().sum()
if faltando > 0:
    print(f"Atenção: {faltando} registros do gabarito não foram encontrados no resultado novo (idx_df1 sem match).")


# Critério de acerto/erro

# Acerto = idx_df2 igual no gabarito e no resultado novo
df_merge["acertou_idx_df2"] = df_merge["idx_df2_gab"] == df_merge["idx_df2_novo"]

total = len(df_merge)
acertos = df_merge["acertou_idx_df2"].sum()
erros = total - acertos

print("------ RESUMO ------")
print(f"Total de casos no gabarito: {total}")
print(f"Acertos (idx_df2 igual):    {acertos}")
print(f"Erros:                      {erros}")
if total > 0:
    print(f"Taxa de acerto:             {acertos/total:.2%}")

# Monta relatório

colunas_relatorio = [
    "idx_df1",

    # dados do CNES / df1 (gabarito)
    "endereco_df1_gab",
    "numero_df1_gab",
    "bairro_df1_gab",

    # match CORRETO (gabarito)
    "idx_df2_gab",
    "endereco_df2_gab",
    "numero_df2_gab",
    "bairro_df2_gab",
    "similaridade_final_gab",

    # match ENCONTRADO no resultado novo
    "idx_df2_novo",
    "endereco_df2_novo",
    "numero_df2_novo",
    "bairro_df2_novo",
    "similaridade_final_novo",

    # flag de acerto/erro
    "acertou_idx_df2",
]

# Merge das colunas
colunas_relatorio = [c for c in colunas_relatorio if c in df_merge.columns]

df_relatorio = df_merge[colunas_relatorio].copy()

df_relatorio = df_relatorio.sort_values(by=["acertou_idx_df2", "similaridade_final_novo"], ascending=[True, False])

# Salva o relatório em Excel
df_relatorio.to_excel(CAMINHO_RELATORIO, index=False)

print(f"\nRelatório detalhado salvo em: {CAMINHO_RELATORIO}")
print("Linhas com 'acertou_idx_df2 = False' são as que o algoritmo errou o match.")
