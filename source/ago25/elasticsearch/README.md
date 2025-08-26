# Como instalar a biblioteca elasticsearch 8

## 1. Adicione a chave GPG e o repositório

```
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
sudo apt-get install apt-transport-https
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee -a /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update
```

## 2. Instale o Elasticsearch

`sudo apt install elasticsearch`

## 3. Configuração Inicial Segura

### 3.1 Localize as senhas iniciais

`sudo cat /etc/elasticsearch/elasticsearch.keystore`

`sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic`

## 4. Ativar Autenticação e TLS

Por padrão, o Elasticsearch 8.x ativa a segurança, mas confira:

`sudo nano /etc/elasticsearch/elasticsearch.yml`

Verifique e ajuste estas configurações:

```
# Segurança e autenticação
xpack.security.enabled: true
xpack.security.enrollment.enabled: true

# Habilitar HTTPS para a API REST
xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12

# Comunicação segura entre nós do cluster
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
```

### 4.1 Restringir o Acesso Externo

`network.host: 127.0.0.1`

## 5. Configurar Usuários e Papéis

Nunca use o usuário `elastic` para tudo. Crie usuários com permissões limitadas:`

`sudo /usr/share/elasticsearch/bin/elasticsearch-users useradd app_user -p "senha_forte" -r read_only`

## 6. Proteção via Firewall

Se o Elasticsearch rodar em produção, libere apenas os IPs necessários:

```
sudo ufw enable
sudo ufw allow from 127.0.0.1 to any port 9200
sudo ufw allow from <IP_DO_SERVIDOR_KIBANA> to any port 9200
sudo ufw status
```


## 7. Testar a Conexão Segura

Use HTTPS e autenticação básica para testar a API:

`curl -u elastic:senha_aqui --cacert /etc/elasticsearch/certs/http_ca.crt https://localhost:9200`

Se der erro o seguinte erro prossiga para o próximo passo:

`curl: (77) error setting certificate file: /etc/elasticsearch/certs/http_ca.crt`

## 8. Configurar arquivo do CA

### 8.1 Verificar se arquivo existe

`sudo ls -l /etc/elasticsearch/certs/http_ca.crt`

Se não existir, procure:

`sudo find /etc/elasticsearch -maxdepth 3 -type f -name "http_ca.crt" -o -name "*ca*.crt"`

### 8.2 Permissões e herança de diretório

Mesmo com `644` no arquivo, o cURL precisa “entrar” nos diretórios. Garanta isso:

```
# diretórios precisam de 'x' (traversal)
sudo chmod 755 /etc/elasticsearch /etc/elasticsearch/certs

# arquivo precisa ser legível por todos
sudo chmod 644 /etc/elasticsearch/certs/http_ca.crt
sudo chown root:root /etc/elasticsearch/certs/http_ca.crt
```

## Resumo 

|          Medida           |             Motivo              |
| ------------------------- | ------------------------------- |
| TLS habilitado            | Protege dados em trânsito       |
| Usuários com papéis       | Evita permissões desnecessárias |
| Firewall configurado      | Reduz superfície de ataque      |
| Certificados automáticos  | Segurança por padrão            |
| Proxy reverso (NGINX)     | Camada extra de proteção        |


## Depois de instalado, verificar status:

### Status

`sudo systemctl status elasticsearch.service`

### Start

`sudo systemctl status elasticsearch.service`

### Stop

`sudo systemctl stop elasticsearch.service`

### Restart

`sudo systemctl restart elasticsearch.service`