## Anotações Importante

### Para a instalação do ElasticSearch:

#### Adicionar repositório da Elastic

```bash
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo tee /usr/share/keyrings/elasticsearch-keyring.asc

echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.asc] \
https://artifacts.elastic.co/packages/8.x/apt stable main" \
| sudo tee /etc/apt/sources.list.d/elastic-8.x.list
```

#### Atualizar e Instalar

```bash
sudo apt update
sudo apt install elasticsearch
```

#### Iniciar e Ativar serviço

```bash
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch
```

### IMPORTANTE:

#### Verifique as permissões do arquivo CA (se estiver utilizando na conexão):

```bash
sudo ls -l /etc/elasticsearch/certs/http_ca.crt

sudo chmod 644 /etc/elasticsearch/certs/http_ca.crt

sudo chmod 755 /etc/elasticsearch

sudo chmod 755 /etc/elasticsearch/certs
```

#### Verifique se está na versão correta:

```bash
pip show elasticsearch
```

A versão deve ser elasticsearch-8.x.x. Se estiver na versão incorreta:

```bash
pip uninstall elasticsearch elastic-transport -y

pip install "elasticsearch<9,>=8.0.0"
```

### Para a execução do LLM

É necessário trocar o ambiente virtual, pois ele roda apenas com python 3.11. Para isso é necessário seguir os seguintes passos:

Se tiver com algum venv ativado:

```bash
deactivate
```

Seguinte:

```bash
cd ~/tcc-culturaeduca/source/nov25/api/

source venv311/bin/activate

python run_comparador.py
```