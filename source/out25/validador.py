import pandas as pd

# ---------------- CONFIGURAÇÕES ----------------

# Arquivo gabarito (onde está "a verdade")
CAMINHO_GABARITO = "results/result_rapidfuzz/result_20251012_142504_analisado_gabarito.xlsx"

# Arquivo NOVO de resultados que você quer validar
# (o que o run_comparador gerou, dentro de results/result_llm/)
CAMINHO_RESULTADO_NOVO = r"results\result_llm\result_20251119_222412.xlsx"  # <<< troque aqui


# Nome da planilha dentro do arquivo novo (run_comparador usa "Enderecos")
SHEET_RESULTADO_NOVO = "Enderecos"

# Arquivo de saída com o relatório de validação
CAMINHO_RELATORIO = "relatorio_validacao_gabarito.xlsx"


# ---------------- CARGA DOS DADOS ----------------

print("Carregando gabarito...")
df_gab = pd.read_excel(CAMINHO_GABARITO)  # primeiro sheet

print("Carregando resultado novo...")
df_novo = pd.read_excel(CAMINHO_RESULTADO_NOVO, sheet_name=SHEET_RESULTADO_NOVO)

# Verifica se idx_df1 é único no gabarito (esperado)
if not df_gab["idx_df1"].is_unique:
    raise ValueError("idx_df1 não é único no gabarito! Isso complica a validação.")

# ---------------- JUNÇÃO PELO idx_df1 ----------------

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


# ---------------- CRITÉRIO DE ACERTO/ERRO ----------------

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

# ---------------- MONTAR RELATÓRIO DETALHADO ----------------

# Vamos montar colunas mais “legíveis” para análise:
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

# Nem sempre todas essas colunas existem nos dois lados;
# então vamos manter só as que realmente existem no df_merge
colunas_relatorio = [c for c in colunas_relatorio if c in df_merge.columns]

df_relatorio = df_merge[colunas_relatorio].copy()

# Ordena deixando erros primeiro (pra você olhar com calma)
df_relatorio = df_relatorio.sort_values(by=["acertou_idx_df2", "similaridade_final_novo"], ascending=[True, False])

# Salva o relatório em Excel
df_relatorio.to_excel(CAMINHO_RELATORIO, index=False)

print(f"\nRelatório detalhado salvo em: {CAMINHO_RELATORIO}")
print("Linhas com 'acertou_idx_df2 = False' são as que o algoritmo errou o match.")
