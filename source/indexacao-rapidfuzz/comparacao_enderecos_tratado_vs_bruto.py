# Comparação usando Rapidfuzz entre endereços tratados (base ouro) e brutos (base CNEFE)

import pandas as pd
from rapidfuzz import process, fuzz
import unidecode

# Normalização de texto
def normalize(text):
    if pd.isna(text):
        return ""
    texto = unidecode.unidecode(str(text)).strip().lower()
    return texto

# Usa um dicionário para substituir abreviações
def normalizar_abreviacoes(texto):
    abreviacoes = {
        " av ": " avenida ",  
        " avn ": " avenida ",
        " r ": " rua ",
        " pc ": " praca ",
        " al ": " alameda ",
        " tr ": " travessa ",
        " jd ": " jardim ",
        " vl ": " vila "
    }
    texto = " " + texto + " " 
    for abrev, completo in abreviacoes.items():
        texto = texto.replace(abrev, completo)
    return texto.strip()  

df_bruto = pd.read_csv("3513801_DIADEMA.csv", sep=";", dtype=str)
df_tratado = pd.read_csv("cnes_geo_padrao_ouro_diadema.csv", sep=";", dtype=str)

# Concatenação dos campos da base bruta
df_bruto["endereco_original"] = (
    df_bruto["NOM_TIPO_SEGLOGR"].fillna("") + " " +
    df_bruto["NOM_TITULO_SEGLOGR"].fillna("") + " " +
    df_bruto["NOM_SEGLOGR"].fillna("") + " " +
    df_bruto["NUM_ENDERECO"].fillna("") + " " +
    df_bruto["DSC_LOCALIDADE"].fillna("")
).apply(normalize)

# Concatenação dos campos da base tratada
df_tratado["endereco_original"] = (
    df_tratado["NO_LOGRADO"].fillna("") + " " +
    df_tratado["NU_ENDEREC"].fillna("") + " " +
    df_tratado["NO_BAIRRO"].fillna("")
).apply(normalize)

# Usa a normalização de abreviações
df_bruto["endereco_normalizado"] = df_bruto["endereco_original"].apply(normalizar_abreviacoes)  
df_tratado["endereco_normalizado"] = df_tratado["endereco_original"].apply(normalizar_abreviacoes)  

df_tratado[["endereco_original", "endereco_normalizado"]].head(10)


# Busca do endereço mais semelhtante usando o RapidFuzz

resultados = []
for idx_tratado, row_tratado in df_tratado.iterrows():
    endereco_t_normalizado = row_tratado["endereco_normalizado"]  
    endereco_t_original = row_tratado["endereco_original"]        

    match, score, idx_bruto = process.extractOne(
        endereco_t_normalizado,                                  
        df_bruto["endereco_normalizado"],                        
        scorer=fuzz.token_set_ratio         # Há palavras extras em um dos lados, mas a maioria está presente nos dois
    )

    endereco_b_original = df_bruto.loc[idx_bruto, "endereco_original"]

    resultados.append({
        "idx_tratado": idx_tratado,
        "endereco_tratado": endereco_t_original,                
        "idx_bruto": idx_bruto,  
        "endereco_bruto": endereco_b_original,                 
        "similaridade": score,
        "endereco_tratado_normalizado": endereco_t_normalizado,
        "endereco_bruto_normalizado": df_bruto.loc[idx_bruto, "endereco_normalizado"],  
    })


# Visualização dos resultados

df_resultados = pd.DataFrame(resultados)

df_resultados['similaridade'] = df_resultados['similaridade'].astype(str).str.replace('.', ',')

df_resultados[["idx_tratado", 
               "endereco_tratado",   
               "idx_bruto",  
               "endereco_bruto",                 
               "similaridade"]].head(10)


# Exporta os resultados em um arquivo CSV
df_resultados.to_csv("enderecos_comparados_tratado_vs_bruto.csv", sep=";", index=False)

