---
title: Visão Geral
layout: home
nav_order: 1
---

# Geocodificação de Endereços Brasileiros com Abordagens Lexicais, Indexadas e Semânticas

Trabalho de Conclusão de Curso desenvolvido no Instituto de Matemática e Estatística da USP, com foco em geocodificação de endereços brasileiros, software livre e análise territorial aplicada à plataforma **CulturaEduca**.

---

## Autoria e orientação

**Autoras:**  
Sabrina Araújo da Silva — NUSP 12566182

Samantha Miyahira — NUSP 11797261

**Orientadora:**  
Profa. Dra. Kelly Rosa Braghetto  

---

## Contexto e motivação

Endereços no Brasil apresentam grande variação de escrita, com abreviações, grafias distintas e informações incompletas. Essas diferenças dificultam a localização precisa dos endereços no território.

A **geocodificação** converte endereços textuais em coordenadas geográficas e é fundamental para plataformas de análise territorial. A plataforma **CulturaEduca**, por exemplo, utiliza dados georreferenciados para analisar o entorno de escolas, equipamentos culturais e serviços públicos, apoiando análises territoriais e o planejamento de ações e políticas públicas.

Além das coordenadas, essas análises dependem da **associação correta do endereço ao setor censitário**, a menor unidade territorial definida pelo IBGE. Vinculações incorretas comprometem diretamente a interpretação espacial dos dados.

Testes com soluções existentes, como o **GeocodeBR**, evidenciaram limitações na identificação adequada dos setores censitários, motivando o desenvolvimento de uma solução própria, baseada em **software livre** e alinhada ao padrão adotado pelo IBGE.

---

## Objetivo do trabalho

O objetivo central deste trabalho é desenvolver um sistema capaz de lidar com a heterogeneidade natural dos endereços brasileiros e produzir uma correspondência consistente entre um endereço textual e o registro mais provável no **Cadastro Nacional de Endereços para Fins Estatísticos (CNEFE)**.

Para isso, foi implementado um sistema modular que combina diferentes estratégias de correspondência aproximada de strings, permitindo avaliar como cada abordagem se comporta diante de abreviações, variações de grafia e dados incompletos.

---

## Abordagem adotada

O sistema desenvolvido explora três estratégias complementares de correspondência:

- **Abordagem lexical**, baseada na biblioteca *RapidFuzz*, que utiliza métricas de similaridade textual e operações sobre tokens;
- **Abordagem baseada em indexação**, utilizando o *Elasticsearch*, que combina mecanismos de busca, tokenização e ranqueamento;
- **Abordagem semântica**, baseada em *embeddings* gerados por modelos de linguagem, permitindo comparar endereços a partir de seu conteúdo semântico.

Todas as abordagens operam sobre entradas previamente normalizadas e são avaliadas a partir de critérios espaciais, com ênfase na correta vinculação dos endereços aos setores censitários.

---

## Cronograma

| Mês               | Atividades                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| Abril – Maio      | Revisão bibliográfica e levantamento das necessidades                        |
| Maio – Junho      | Escolha e prototipação das abordagens e ferramentas                          |
| Junho – Outubro    | Desenvolvimento da ferramenta de geocodificação                              |
| Novembro           | Avaliação dos métodos, testes, análise dos resultados e refinamento                                 |
| Outubro – Dezembro| Redação e finalização do Trabalho de Conclusão de Curso                      |

---

## Trabalho final

**Monografia**:

[PDF do trabalho final](/tcc-culturaeduca/docs/monografia.pdf)

**Repositório do código**

A implementação do sistema foi disponibilizada em repositório público, reunindo os principais componentes do trabalho desenvolvido.

[Repositório no GitHub](https://github.com/sabrizzs/tcc-culturaeduca)

**Poster**:

[Poster do trabalho final](/tcc-culturaeduca/docs/poster.pdf)
