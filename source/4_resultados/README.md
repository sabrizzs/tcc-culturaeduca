# Resultados e análises no PostgreSQL

Esta etapa foi usada inicialmente para uma visão geral dos resultados via arquivos locais, mas **as tabelas finais de análise e consolidação foram geradas no PostgreSQL (com PostGIS)**.

A lógica é, em alto nível:

1. **Criar a tabela de staging** (estrutura compatível com o CSV de resultados).
2. **Importar o CSV** com `COPY`.
3. **Gerar a tabela/consulta final**:
   - calcular a **mediana** de `(lat, lon)` por entidade (`idx_df1` ou `_id`);
   - calcular o setor censitário **onde o ponto caiu** (`cd_setor_geom`) via `ST_Contains`;
   - ranquear candidatos por um critério estável (`ROW_NUMBER() OVER (...)`);
   - selecionar **apenas o melhor candidato** (`WHERE rn = 1`);
   - derivar campos de avaliação: `setor_correspondente`, `dist_ate_setor_ref_m`, etc.

---

## Exemplo: resultado do LLM (Diadema)

### 1) Criar tabela

```sql
CREATE TABLE public.resultado_diadema_llm (
    idx_df1               BIGINT,
    endereco_df1          TEXT,
    numero_df1            DOUBLE PRECISION,
    complemento_df1       TEXT,
    bairro_df1            TEXT,

    idx_df2               BIGINT,
    cod_unico_df2         BIGINT,
    endereco_df2          TEXT,
    numero_df2            DOUBLE PRECISION,
    complemento_df2       TEXT,
    bairro_df2            TEXT,

    similaridade_logradouro DOUBLE PRECISION,
    similaridade_numero      DOUBLE PRECISION,
    similaridade_bairro      DOUBLE PRECISION,
    similaridade_final       DOUBLE PRECISION,

    latitude_verdadeira   DOUBLE PRECISION,
    longitude_verdadeira  DOUBLE PRECISION,
    cd_setor_verdadeiro   TEXT,

    latitude_resultante   DOUBLE PRECISION,
    longitude_resultante  DOUBLE PRECISION,
    cd_setor_resultante   TEXT
);
```

### 2) Importar CSV para a tabela

```sql
COPY resultado_diadema_llm
FROM 'result_diadema_llm_20251209_011305.csv'
DELIMITER ';'
CSV HEADER
NULL ''
QUOTE '"'
ESCAPE '"';
```

### 3) Consulta final de análise (desempate e métricas)

Considerações iniciais:

- a tabela `eq_educacao_basica_2024` é um arquivo de entrada que contém o setor esperado.
- a tabela `dtb_setores_censitarios_2022` armazena a malha de setores censitários brasileiros de 2022 com colunas _geom (geometry) e _geog (geography).

```sql
WITH medianas AS (
    SELECT
        idx_df1,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY latitude_resultante)  AS med_lat,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY longitude_resultante) AS med_lon
    FROM public.resultado_diadema_llm
    GROUP BY idx_df1
),
pontos_com_setor AS (
    SELECT
        g.*,
        g.ctid AS ctid,
        s.cd_setor AS cd_setor_geom
    FROM public.resultado_diadema_llm g
    LEFT JOIN dtb_setores_censitarios_2022 s
      ON ST_Contains(
           s._geom,
           ST_SetSRID(ST_MakePoint(g.longitude_resultante, g.latitude_resultante), 4326)
         )
),
candidatos AS (
    SELECT
        p.*,
        m.med_lat,
        m.med_lon,

        -- distância até a mediana do grupo (estabiliza “empates”)
        ST_DistanceSphere(
            ST_MakePoint(p.longitude_resultante, p.latitude_resultante),
            ST_MakePoint(m.med_lon, m.med_lat)
        ) AS dist_mediana,

        e.cd_setor_2022 AS cd_setor_ref,

        -- distância entre ponto verdadeiro e ponto estimado
        ST_DistanceSphere(
            ST_MakePoint(p.longitude_verdadeira, p.latitude_verdadeira),
            ST_MakePoint(p.longitude_resultante, p.latitude_resultante)
        ) AS distancia_original_m,

        ROW_NUMBER() OVER (
            PARTITION BY p.idx_df1
            ORDER BY
                -- 1) setor igual ao esperado?
                (p.cd_setor_geom = e.cd_setor_2022) DESC,

                -- 2) cair dentro de qualquer setor
                (p.cd_setor_geom IS NOT NULL) DESC,

                -- 3) melhor precisão (se existir no dataset)
                CASE p.precisao
                    WHEN 'numero'     THEN 1
                    WHEN 'logradouro' THEN 2
                    WHEN 'bairro'     THEN 3
                    WHEN 'municipio'  THEN 4
                    ELSE 5
                END ASC,

                -- 4) menor desvio (se existir no dataset)
                p.desvio_metros ASC,

                -- 5) menor distância até a mediana
                ST_DistanceSphere(
                    ST_MakePoint(p.longitude_resultante, p.latitude_resultante),
                    ST_MakePoint(m.med_lon, m.med_lat)
                ) ASC,

                -- 6) critério estável: primeira linha inserida
                p.ctid
        ) AS rn
    FROM pontos_com_setor p
    JOIN medianas m
      ON m.idx_df1 = p.idx_df1
    LEFT JOIN eq_educacao_basica_2024 e
      ON e._id = p.idx_df1
)
SELECT
    c.*,

    -- 1) setor_correspondente: true se geom == ref, false caso contrário
    COALESCE(c.cd_setor_geom = c.cd_setor_ref, false) AS setor_correspondente,

    -- 2) distância até o setor correto (em metros)
    CASE
        WHEN COALESCE(c.cd_setor_geom = c.cd_setor_ref, false) THEN
            0::double precision
        WHEN s_ref._geog IS NULL THEN
            NULL::double precision
        ELSE
            ST_Distance(
                ST_SetSRID(ST_MakePoint(c.longitude_resultante, c.latitude_resultante), 4326)::geography,
                s_ref._geog
            )
    END AS dist_ate_setor_ref_m

FROM candidatos c
LEFT JOIN dtb_setores_censitarios_2022 s_ref
  ON s_ref.cd_setor = c.cd_setor_ref
WHERE c.rn = 1;
```

## Geocodebr (R): gerar resultados e importar no Postgres

O `geocodebr` gera colunas com nomes diferentes (ex.: lat, lon, etc.). Por isso, após importar o CSV para uma tabela de staging, a consulta de análise deve referenciar esses nomes.

### 1) Script R para geocodificar (geocodebr)

```r
#!/usr/bin/env Rscript

# ========================
# geocodificacao.R
# Uso:
#   Rscript geocodificacao.R
# ========================

entrada <- "C:/Users/samantha/OneDrive/Área de Trabalho/tcc/cnes_geo_padrao_ouro_diadema_com_virgula.csv"
saida   <- "C:/Users/samantha/OneDrive/Área de Trabalho/tcc/result_cnes_diadema_geocodebr_certo.csv"

message(">> Arquivo de entrada: ", entrada)
message(">> Arquivo de saída  : ", saida)
message(">> Workers           : ", workers)

# -----------------------
# Instala/Carrega pacotes
# -----------------------
ensure_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
}

ensure_pkg("geocodebr")
ensure_pkg("readr")
ensure_pkg("dplyr")

# -----------------------
# Ler CSV (ajuste encoding/sep se preciso)
# -----------------------
message(">> Lendo CSV...")

df <- readr::read_csv(entrada, show_col_types = FALSE, progress = TRUE) # quando o separado é ,


df$no_municipio <- "Diadema" # adiciona coluna
df$sg_uf <- "SP" # adiciona coluna

col_logradouro <- "NO_LOGRADO"
col_numero     <- "NU_ENDEREC"
col_bairro     <- "NO_BAIRRO"
col_municipio  <- "no_municipio"
col_uf         <- "sg_uf"
col_cep        <- "CO_CEP"      # opcional (o geocodebr usa para validação)


# Garante que existam
required_cols <- c(col_logradouro, col_numero, col_bairro, col_municipio, col_uf)
missing_cols  <- setdiff(required_cols, names(df))
if (length(missing_cols) > 0) {
  stop("Colunas ausentes no CSV: ", paste(missing_cols, collapse = ", "))
}

# -----------------------
# Mapear campos para o geocodebr
# -----------------------
message(">> Definindo mapeamento de campos...")
campos <- geocodebr::definir_campos(
  estado     = col_uf,
  municipio  = col_municipio,
  logradouro = col_logradouro,
  numero     = col_numero,
  localidade = col_bairro   # bairro
)

# -----------------------
# Geocodificar
# -----------------------

message(">> Geocodificando... isto pode levar alguns minutos.")

tempo <- system.time({
  res <- geocodebr::geocode(df, campos)
})

message(">> Tempo de geocodificação:")
print(tempo)

# -----------------------
# Salvar resultado
# -----------------------
message(">> Salvando CSV de saída: ", saida)
readr::write_csv(res, saida)

message("✅ Concluído com sucesso!")
```

## Exemplo: análise no Postgres para resultados do geocodebr (Diadema)

Após criar a tabela public.diadema_geocodebr e importar o CSV, execute a consulta final abaixo.

```sql
WITH medianas AS (
    SELECT
        _id,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY lat) AS med_lat,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY lon) AS med_lon
    FROM public.roraima_geocodebr
    GROUP BY _id
),
pontos_com_setor AS (
    SELECT
        g.*,
		g.ctid AS ctid,
        s.cd_setor AS cd_setor_geom
    FROM public.roraima_geocodebr g
    LEFT JOIN dtb_setores_censitarios_2022 s
      ON ST_Contains(
           s._geom,
           ST_SetSRID(ST_MakePoint(g.lon, g.lat), 4326)
         )
),
candidatos AS (
    SELECT
        p.*,
        m.med_lat,
        m.med_lon,
        -- distância até a mediana
        ST_DistanceSphere(
            ST_MakePoint(p.lon, p.lat),
            ST_MakePoint(m.med_lon, m.med_lat)
        ) AS dist_mediana,
        e.cd_setor_2022 AS cd_setor_ref,
		ST_DistanceSphere(
		    ST_MakePoint(p.longitude, p.latitude),
		    ST_MakePoint(p.lon, p.lat)
		) AS distancia_original_m,

        ROW_NUMBER() OVER (
            PARTITION BY p._id
            ORDER BY
                -- 1) setor igual ao esperado?
                (p.cd_setor_geom = e.cd_setor_2022) DESC,

                -- 2) cair dentro de qualquer setor
                (p.cd_setor_geom IS NOT NULL) DESC,

                -- 3) melhor precisão
                CASE p.precisao
                    WHEN 'numero'     THEN 1
                    WHEN 'logradouro' THEN 2
                    WHEN 'bairro'     THEN 3
                    WHEN 'municipio'  THEN 4
                    ELSE 5
                END ASC,

                -- 4) menor desvio
                p.desvio_metros ASC,

                -- 5) menor distância até a mediana (repetir expressão!)
                ST_DistanceSphere(
                    ST_MakePoint(p.lon, p.lat),
                    ST_MakePoint(m.med_lon, m.med_lat)
                ) ASC,

                -- 6) último critério estável - linha que foi inserida primeira no postgres
                p.ctid
        ) AS rn

    FROM pontos_com_setor p
    JOIN medianas m USING (_id)
    LEFT JOIN eq_educacao_basica_2024 e USING (_id)
)

SELECT 
    c.*,

    -- 1) setor_correspondente: true se geom == ref, false caso contrário
    COALESCE(c.cd_setor_geom = c.cd_setor_ref, false) AS setor_correspondente,

    -- 2) distância até o setor correto (em metros)
    CASE
        WHEN COALESCE(c.cd_setor_geom = c.cd_setor_ref, false) THEN
            0::double precision  -- já está no setor correto → distância 0
        WHEN s_ref._geog IS NULL THEN
            NULL::double precision  -- não temos setor de referência → distância indefinida
        ELSE
            ST_Distance(
                ST_SetSRID(ST_MakePoint(c.lon, c.lat), 4326)::geography,
                s_ref._geog  -- geografia do setor de referência
            )
    END AS dist_ate_setor_ref_m

FROM candidatos c
LEFT JOIN dtb_setores_censitarios_2022 s_ref
  ON s_ref.cd_setor = c.cd_setor_ref
WHERE c.rn = 1;
```

Por fim, as tabelas resultantes são gravadas em CSV para gerar os gráficos na próxima etapa.