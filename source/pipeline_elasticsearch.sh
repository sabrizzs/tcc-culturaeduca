#!/usr/bin/env bash
set -euo pipefail

# Carrega variáveis do arquivo .env
source .env
PYTHON="python"

echo "Executando com variáveis:"
echo "PROJ_DIR=$PROJ_DIR"
echo "PYTHON=$PYTHON"

cd "$PROJ_DIR"

echo "==============================="
echo "Rodando NORMALIZAÇÃO - CNEFE"
echo "==============================="
$PYTHON normalizacao/normalizacao.py  @input_normalizacao_cnefe.txt

echo "==============================="
echo "Rodando NORMALIZAÇÃO - ENTRADA"
echo "==============================="
$PYTHON normalizacao/normalizacao.py  @input_normalizacao_entrada.txt

echo "=============================="
echo "Rodando INDEXAÇÃO"
echo "=============================="
$PYTHON indexacao/indexacao.py

echo "=============================="
echo "Rodando GEOCODIFICAÇÃO"
echo "=============================="
$PYTHON geocodificacao/geocodificacao.py

echo "=============================="
echo "Pipeline concluída com sucesso!"
echo "=============================="
