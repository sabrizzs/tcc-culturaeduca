
# Ferramentas de Indexação de Texto

Recomendações organizadas por **categoria**, com foco em **busca textual**, **bancos de dados** e **gerenciamento de texto**.

---

## 🔍 Motores de Busca Textual / Full-Text Search Engines

Ideais para **indexação e busca eficiente em textos grandes ou estruturados**.

| Ferramenta        | Destaques                                                                 |
|-------------------|--------------------------------------------------------------------------|
| **Elasticsearch** | Busca full-text, escalável, RESTful, muito usado em logs, sites e apps. |
| **Apache Solr**   | Baseado em Lucene, altamente configurável e poderoso.                   |
| **Meilisearch**   | Motor de busca leve, muito rápido e fácil de usar.                      |
| **Typesense**     | Alternativa moderna ao Elasticsearch, ótima para autocompletar.         |
| **Whoosh**        | 100% Python puro, bom para projetos pequenos e locais.                  |

---

## 🗃️ Bancos de Dados com Suporte a Indexação de Texto

Bancos com **busca textual embutida**.

| Banco de Dados         | Suporte a Texto                                                           |
|------------------------|---------------------------------------------------------------------------|
| **PostgreSQL**         | Suporte a `tsvector` / `tsquery` com `GIN` index para full-text search. |
| **MongoDB**            | Suporte a índices textuais (`text index`) em campos específicos.         |
| **SQLite**             | Usa o módulo FTS5 para busca textual. Ideal para apps locais.            |
| **MySQL**              | Oferece `FULLTEXT` index em tabelas InnoDB ou MyISAM.                    |

---

## 🧠 Bibliotecas de NLP com Funções de Indexação

Para **customização com NLP e pré-processamento de texto**.

| Ferramenta      | Descrição                                                                 |
|-----------------|---------------------------------------------------------------------------|
| **spaCy**       | NLP rápido, ideal para tokenização antes da indexação.                   |
| **NLTK**        | Biblioteca clássica de NLP em Python, útil para análise prévia.          |
| **Gensim**      | Focado em vetorização de texto e busca semântica (e.g. LSI, Word2Vec).   |
| **Haystack**    | Framework para criar buscadores baseados em modelos como BERT.           |

---

## 🗂️ Gerenciadores de Documentos / DMS

Para **armazenamento e indexação de documentos com OCR e busca**:

| Ferramenta             | Recursos                                                                |
|------------------------|-------------------------------------------------------------------------|
| **Docspell**           | DMS para documentos escaneados com OCR, etiquetas e busca.              |
| **Paperless-ngx**      | OCR + indexação automática, ideal para uso pessoal ou pequeno time.     |
| **Mayan EDMS**         | DMS completo com workflow, OCR e busca textual.                         |

---

## 🔧 Outros Úteis para Integração

- **Apache Lucene** – Biblioteca base usada por Elasticsearch e Solr.
- **OpenSearch** – Fork do Elasticsearch mantido pela AWS.
- **Tantivy** – Motor de busca em Rust, inspirado no Lucene.
