
# TCC CulturaEduca

Este repositório contém o código-fonte, documentação e materiais relacionados ao Trabalho de Conclusão de Curso (TCC) desenvolvido para a plataforma [CulturaEduca](https://culturaeduca.cc/). O projeto aborda técnicas de geocodificação e visualização de dados aplicadas à análise territorial, utilizando software livre e dados públicos.

[**Site do projeto**](https://sabrizzs.github.io/tcc-culturaeduca/)

[**Monografia**](/site/docs/monografia.pdf)

[**Poster**](/site/docs/poster.pdf)

---

## Objetivo do Projeto

O objetivo principal é desenvolver uma solução capaz de realizar geocodificação de endereços brasileiros com maior precisão, considerando a heterogeneidade das formas de escrita e garantindo a correspondência correta com setores censitários do IBGE. Essa funcionalidade é essencial para análises espaciais voltadas à educação, cultura e políticas públicas.

---

## Estrutura do Repositório

A organização do repositório segue duas áreas principais:

- **`source/`**  
  Contém o código-fonte do sistema, incluindo scripts para pré-processamento, algoritmos de correspondência e integração com bases de dados.

- **`site/`**  
  Diretório dedicado à documentação do projeto, publicado via GitHub Pages.
  - `index.md`: página inicial do site do TCC.
 
  - **`site/docs/`**  
  Contém os arquivos em PDF relacionados ao trabalho:
    - `monografia.pdf`: versão final da monografia.
    - `poster.pdf`: pôster do trabalho.

---

## Principais Funcionalidades

- **Geocodificação baseada em múltiplas abordagens**:
  - Similaridade lexical com RapidFuzz.
  - Indexação e busca com Elasticsearch.
  - Correspondência semântica utilizando *embeddings* de modelos de linguagem.

- **Integração com o Cadastro Nacional de Endereços para Fins Estatísticos (CNEFE)**:
  - Base oficial do IBGE para endereços georreferenciados.

- **Visualização e análise territorial**:
  - Ferramentas para mapear resultados e associar endereços a setores censitários.
