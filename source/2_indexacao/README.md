# Pré-processamento: Embeddings (LLM) e Indexação (Elasticsearch)

Este módulo realiza o pré-processamento necessário para a etapa de correspondência de endereços, preparando duas estruturas fundamentais:

- **Embeddings baseados em LLM** armazenados no **PostgreSQL (pgvector)**  
- **Índice de busca textual** no **Elasticsearch**, baseado nos dados normalizados do CNEFE

O objetivo é permitir comparações eficientes entre endereços por similaridade semântica e por busca indexada.

---

## Estrutura dos Scripts

- `embeddings_llm.py`  
  Gera embeddings de **logradouro**, **número** e **bairro** a partir de um CSV normalizado e armazena os vetores no PostgreSQL.

- `indexacao_elasticsearch.py`  
  Cria e popula um índice no Elasticsearch a partir do arquivo normalizado do CNEFE.

---

## Requisitos

- Python 3.x  
- PostgreSQL com extensão **pgvector** habilitada  
- Elasticsearch acessível em `https://localhost:9200`  
- Bibliotecas Python listadas nos próprios scripts (`pandas`, `psycopg2`, `sentence-transformers`, `elasticsearch`, etc.)

---

## 1. Geração de Embeddings (LLM)

### Configuração

No arquivo `embeddings_llm.py`, ajuste os seguintes parâmetros:

- `ARQUIVO_ENTRADA`: caminho do CSV normalizado  
- `COD_UNICO`: coluna identificadora única do endereço  
- `TABELA_EMBEDDINGS`: nome da tabela no PostgreSQL onde os embeddings serão armazenados  

A conexão com o PostgreSQL é feita via variável de ambiente:

```bash
export PG_DSN="dbname=... user=... password=... host=... port=..."
```

## 2. Indexação (Elasticsearch)

### Configuração

No arquivo `indexacao_elasticsearch.py`, ajuste:

- `arquivo_cnefe_normalizado`: caminho do CSV normalizado do CNEFE
- Credenciais de acesso ao Elasticsearch
