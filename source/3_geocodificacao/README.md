# Comparação de endereços (RapidFuzz, Elasticsearch, LLM/Embeddings)

Esta etapa contém módulos para **comparar endereços entre dois DataFrames** (df1 = “entrada”, df2 = “base/CNEFE”), gerando um DataFrame de resultados padronizado com scores e informações espaciais (lat/lon e setor censitário).

Há três abordagens:
1. **RapidFuzz (lexical)**: fuzzy matching em texto, com paralelismo por threads.
2. **Elasticsearch (indexada)**: busca aproximada no índice com boosts e bônus de proximidade do número.
3. **LLM/Embeddings via Postgres (pgvector)**: busca de vizinhos por distância vetorial no banco e conversão para “similaridade”. 

---

## Estrutura (arquivos principais)

- `run_comparador.py`: script principal
- `comparador.py`: função `comparar(...)` e utilitário `formatar_endereco(...)`.
- `rapidfuzz_module.py`: `executar_rapidfuzz(...)`.
- `elasticsearch_module.py`: `executar_elasticsearch(...)` + funções de busca no ES. 
- `llm_module.py`: `executar_llm(...)` consultando embeddings no Postgres.
- `entrada_diadema.txt`: parâmetros/colunas usados em uma execução, para o caso de Diadema.   

---

## Antes de executar run_comparador.py:

É necessario ajustar os parametros do arquivo de entrada:

```
--algoritmo
<rapidfuzz, elasticsearch ou llm>
--local_base_dados
<nome do local>
--arquivo_entrada
<caminho do arquivo de entrada normalizado>
--arquivo_base_cnefe
<caminho do arquivo do cnefe normalizado>
...
```

---

## Execução de cada método:

Considerando que o arquivo de entrada seja `entrada.txt`:

### RapidFuzz

Atualize o algoritmo do arquivo de entrada:

```
--algoritmo
rapidfuzz
```

Após isso execute:

```
python run_comparador.py @entrada.txt
```

### Elasticsearch

Atualize o algoritmo do arquivo de entrada:

```
--algoritmo
elasticsearch
```

Após isso execute:

```
python run_comparador.py @entrada.txt
```

### LLM

Antes de executar, é necessário atualizar o nome das tabelas na consulta do arquivo `llm_module.py`:

```
cur.execute(
    """
    SELECT
        ...
    FROM <nome tabela de entrada> e
    JOIN <nome tabela do cnefe> c ON TRUE`
        ...
```

Essas tabelas foram criadas na etapa anterior que contem os embeddings dos datasets de entrada e do cnefe.

Atualize o algoritmo do arquivo de entrada:

```
--algoritmo
llm
```

Depois de atualizar, execute com o seguinte comando:

```
python run_comparador.py @entrada.txt
```