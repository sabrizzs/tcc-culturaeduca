# Visão geral de execução do projeto

O projeto está organizado em **etapas sequenciais**, cada uma correspondente a uma pasta específica.  
A execução **deve seguir rigorosamente a ordem abaixo**, pois cada etapa depende dos resultados gerados na anterior.

## Estrutura do projeto

1. **`normalizacao/`**  
   Padronização e limpeza dos dados de entrada (endereços e atributos auxiliares).

2. **`indexacao/`**  
   Pré-processamento e construção de estruturas de apoio à busca (ex.: índices, vetores, bases auxiliares).

3. **`geocodificacao/`**  
   Execução dos métodos de geocodificação e comparação de endereços (RapidFuzz, Elasticsearch, GeoCodeBR, LLM).

4. **`resultados/`**  
   Consolidação, desempate espacial e avaliação dos resultados no PostgreSQL/PostGIS.

5. **`geracao_de_graficos/`**  
   Análise visual e geração de gráficos comparativos a partir dos resultados finais.

---

## Leitura obrigatória

Cada pasta contém um **`README.md` próprio**, com instruções específicas, dependências adicionais e observações importantes.  
**É altamente recomendável ler o README de cada etapa antes de executar qualquer código**, pois há parâmetros, caminhos e pré-requisitos essenciais para a correta reprodução dos resultados.

---

## Instalação das dependências

Crie um ambiente virtual (opcional, mas recomendado) e instale as dependências do projeto:

```bash
pip install -r requirements.txt
