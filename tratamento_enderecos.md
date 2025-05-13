---
title: Tratamento e Indexação de Endereços
nav_order: 3
parent: Documentação do Projeto
---

## 3.1. Problema inicial: inconsistência nos dados de endereço e opções para tratamento textual

Durante a fase inicial do projeto, identificamos um dos principais desafios na integração da ferramenta de geocodificação à plataforma **CulturaEduca**: a inconsistência dos dados de endereço provenientes de diferentes bases. Muitas vezes, os endereços chegam incompletos, abreviados ou com variações de escrita, o que inviabiliza a correspondência direta com a base oficial de referência, como o **Cadastro Nacional de Endereços para Fins Estatísticos (CNEFE)**.

Exemplos práticos incluem a abreviação de `Barão` como `Bar.`, a omissão do tipo de via (`Rua`, `Avenida`, `Praça`), ou ainda a mistura de campos como número e complemento em uma mesma string. Essa heterogeneidade compromete a qualidade da geocodificação e, consequentemente, a associação correta com o setor censitário, essencial para a análise espacial dentro da plataforma.

### Abordagens consideradas

- **Algoritmos de similaridade textual**  
  Utilização de métricas como *Levenshtein*, *Jaro-Winkler* e *TF-IDF* para calcular a distância entre duas strings e sugerir o endereço mais próximo, mesmo quando há erros de digitação, abreviações ou omissões.

- **Modelos de linguagem (LLMs)**  
  Aplicação de modelos de linguagem treinados para auxiliar na **separação automática de campos** (ex: nome da via, número, complemento) e na **interpretação contextual** de endereços incompletos ou ambíguos.

- **Estruturas de indexação para busca aproximada**  
  Avaliação do uso de **árvores BK**, **trigrams** e **índices vetoriais** para construir uma base consultável de endereços que permita realizar **buscas por similaridade** com desempenho eficiente.

Essas abordagens são complementares e podem ser combinadas em etapas, desde o pré-processamento dos dados, passando pela normalização dos termos, até a etapa de busca e associação final. O objetivo é garantir que o sistema seja capaz de reconhecer diferentes formas de se referir a um mesmo local, permitindo uma geocodificação confiável e adaptável à realidade dos dados públicos.

Nos próximos capítulos, detalharemos os testes realizados com essas técnicas, os critérios de escolha e os resultados obtidos com dados reais da plataforma.
