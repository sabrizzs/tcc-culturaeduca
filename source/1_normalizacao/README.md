### Executar Normalização

`python run_normalizacao @<nome_do_arquivo.txt>`

### Arquivos de input

Nos arquivos `input_normalizacao_cnefe.txt` e `input_normalizacao_entrada.txt`, substituir os textos de cada arquivo conforme as informações abaixo, de acordo com a base de dados que está utilizando:

Observação: substitua o caminho do arquivo abaixo de ``--arquivo_dataset`

#### Diadema

1) cnefe

```
--tipo_dados
cnefe
--local_base_dados
diadema
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/3513801_DIADEMA.csv
--separador_arq_dataset
;
--colunas_logradouro_dataset
NOM_TIPO_SEGLOGR
NOM_TITULO_SEGLOGR
NOM_SEGLOGR
--coluna_bairro_dataset
DSC_LOCALIDADE
--coluna_numero_dataset
NUM_ENDERECO
--coluna_cd_setor_dataset
COD_SETOR
```

2) entrada

```
--tipo_dados
entrada
--local_base_dados
diadema
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/cnes_geo_padrao_ouro_diadema.csv
--separador_arq_dataset
,
--colunas_logradouro_dataset
NO_LOGRADO
--coluna_bairro_dataset
NO_BAIRRO
--coluna_numero_dataset
NU_ENDEREC
--coluna_cd_setor_dataset
CD_SETOR
```

#### Município de São Paulo

1) cnefe

```
--tipo_dados
cnefe
--local_base_dados
sao paulo
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/cnefe_MUN_SP.csv
--separador_arq_dataset
;
--colunas_logradouro_dataset
NOM_TIPO_SEGLOGR
NOM_TITULO_SEGLOGR
NOM_SEGLOGR
--coluna_bairro_dataset
DSC_LOCALIDADE
--coluna_numero_dataset
NUM_ENDERECO
--coluna_cd_setor_dataset
COD_SETOR
```

2) entrada

```
--tipo_dados
entrada
--local_base_dados
sao paulo
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/educacao_2024_MUN_SP.csv
--separador_arq_dataset
,
--colunas_logradouro_dataset
ds_endereco
--coluna_bairro_dataset
no_bairro
--coluna_numero_dataset
nu_endereco
--coluna_cd_setor_dataset
cd_setor_2022
```

#### Rondônia

1) cnefe

```
--tipo_dados
cnefe
--local_base_dados
rondonia
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/cnefe_RO.csv
--separador_arq_dataset
;
--colunas_logradouro_dataset
NOM_TIPO_SEGLOGR
NOM_TITULO_SEGLOGR
NOM_SEGLOGR
--coluna_bairro_dataset
DSC_LOCALIDADE
--coluna_numero_dataset
NUM_ENDERECO
--coluna_cd_setor_dataset
COD_SETOR
```

2) entrada

```
--tipo_dados
entrada
--local_base_dados
rondonia
--arquivo_dataset
/home/samantha/tcc-culturaeduca/source/nov25/api/datasets/educacao_2024_RO.csv
--separador_arq_dataset
,
--colunas_logradouro_dataset
ds_endereco
--coluna_bairro_dataset
no_bairro
--coluna_numero_dataset
nu_endereco
--coluna_cd_setor_dataset
cd_setor_2022
```