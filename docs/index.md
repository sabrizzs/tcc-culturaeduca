---
title: Início
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

O trabalho com endereços no Brasil envolve, inevitavelmente, uma grande variedade de formas de escrita. Um mesmo logradouro pode aparecer abreviado em uma base de dados, por extenso em outra ou conter erros de digitação e informações incompletas. Embora essas variações pareçam pequenas, elas se tornam um obstáculo concreto quando se busca localizar endereços com precisão no território.

O processo responsável por essa localização é a **geocodificação**, que transforma uma descrição textual de endereço em coordenadas geográficas. Plataformas que realizam análises territoriais dependem diretamente dessa conversão. Esse é o caso da plataforma **CulturaEduca**, que utiliza dados georreferenciados para analisar o entorno de escolas, equipamentos culturais e serviços públicos, apoiando diagnósticos territoriais e o planejamento de ações comunitárias e políticas públicas.

No entanto, a geocodificação não se limita à obtenção de coordenadas. Parte significativa das análises do CulturaEduca depende da **associação correta entre o endereço e o setor censitário correspondente**, que é a menor unidade territorial utilizada pelo IBGE para fins estatísticos. Quando um endereço é vinculado ao setor incorreto, toda a interpretação espacial é comprometida.

Tentativas iniciais de utilizar soluções existentes, como o pacote **GeocodeBR**, revelaram limitações práticas, especialmente na identificação correta dos setores censitários. Essas dificuldades motivaram o desenvolvimento de uma solução própria, baseada em **software livre** e alinhada ao padrão de referência adotado pelo IBGE.

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

**Monografia (PDF)**:

[PDF do trabalho final](./monografia.pdf)

**Repositório do código**

A implementação completa do sistema foi disponibilizada em um repositório público, de forma a permitir a reprodutibilidade dos experimentos e o reaproveitamento da solução por outras iniciativas acadêmicas e públicas.

[Repositório no GitHub](https://github.com/sabrizzs/tcc-culturaeduca)
