# 🦉 CorujaZap - Sistema de Análise de Mensagens WhatsApp

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Sistema completo para análise e visualização de dados de mensagens WhatsApp exportadas. Desenvolvido para suporte a operações de investigação e análise forense digital.

## 📋 Índice

- [Características](#-características)
- [Instalação](#-instalação)
- [Instalação com Docker](#-instalação-com-docker-recomendado)
- [Configuração Manual do Banco](#-configuração-manual-do-banco)
- [Funcionalidades](#-funcionalidades)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Como Usar](#-como-usar)
- [API e Endpoints](#-api-e-endpoints)
- [Solução de Problemas](#-solução-de-problemas)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

## 🚀 Características

- **Interface Web Moderna**: Desenvolvida em Streamlit com design responsivo
- **Análise Multidimensional**: Visualizações interativas de dados de mensagens
- **Geolocalização**: Mapeamento de IPs com dados geográficos
- **Análise Temporal**: Gráficos de atividade por períodos
- **Gestão de Operações**: Sistema multi-operação com isolamento de dados
- **Processamento de Arquivos**: Processamento automático de exports WhatsApp
- **Visualizações Avançadas**: Mapas interativos, gráficos e dashboards
- **Enriquecimento de Dados**: APIs para dados geográficos e de ISPs
- **Containerização**: Deploy simplificado com Docker

## 📦 Instalação

### Pré-requisitos

- **Docker** e **Docker Compose** (Recomendado)
- **Python 3.13+** (para instalação local)
- **Git**

## 🐳 Instalação com Docker (Recomendado)

### Método 1: Docker Compose (Mais Simples)

1. **Clone/extraia o projeto:**
```bash
cd corujazap
```

2. **Configure as variáveis de ambiente:**
```bash
# O arquivo .env já está configurado com os valores padrão
# Edite se necessário
```

3. **Criar rede Docker:**
```bash
docker network create corujazap-net
```

4. **Executar com Docker Compose:**
```bash
# Inicializar todos os serviços
docker-compose up --build -d

# Verificar status
docker-compose ps
```

5. **Acessar a aplicação:**
```
Aplicação: http://localhost:8501
```

### Método 2: Docker Manual

1. **Criar rede Docker:**
```bash
docker network create corujazap-net
```

2. **Executar MySQL:**
```bash
docker run -d --name corujazap_db \
  --network corujazap-net \
  -e MYSQL_ROOT_PASSWORD=admin \
  -e MYSQL_DATABASE=corujazap_db \
  -v mysql_data:/var/lib/mysql \
  -v "$(pwd)/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
  -p 3306:3306 \
  mysql:8.0 --log-bin-trust-function-creators=1
```

3. **Construir e executar aplicação:**
```bash
# Construir imagem
docker build -t corujazap-app .

# Executar aplicação
docker run -d --name corujazap_app \
  --network corujazap-net \
  -e DB_HOST=corujazap_db \
  -e DB_USER=root \
  -e DB_PASSWORD=admin \
  -e DB_NAME=corujazap_db \
  -v "$(pwd):/corujazap" \
  -p 8501:8501 \
  corujazap-app
```

### Comandos Úteis do Docker

```bash
# Ver logs da aplicação
docker compose logs app

# Ver logs do MySQL
docker compose logs mysql

# Parar todos os serviços
docker compose down

# Reiniciar com rebuild
docker compose up --build -d

# Entrar no container da aplicação
docker exec -it corujazap_app sh

# Backup do banco de dados
docker exec corujazap_db mysqldump -u root -padmin corujazap_db > backup.sql
```


## 🛠️ Funcionalidades

### 1. 📊 Dashboard Principal
- **Visão geral das operações** ativas
- **Métricas em tempo real** de mensagens processadas
- **Gráficos de atividade** por período
- **Status de processamento** de arquivos

### 2. ⚙️ Administração
- **Gestão de Operações**: Criar, editar e selecionar operações
- **Gestão de Pacotes**: Upload e processamento de arquivos WhatsApp
- **Configurações do Sistema**: Parâmetros globais

### 3. 🗺️ Geolocalização de IPs
- **Mapa Interativo**: Visualização geográfica com Folium
- **Cluster de Marcadores**: Agrupamento automático por proximidade
- **Filtros Avançados**: Por sender, período e intensidade
- **Análise Geográfica**: Distribuição por países, cidades e ISPs
- **Export de Dados**: Download em CSV dos resultados

### 4. 📱 Análise de Dados WhatsApp
- **Agenda de Contatos**: Visualização e análise de contatos
- **Grupos**: Informações sobre grupos e participantes
- **Mensagens**: Timeline detalhada de conversas
- **Padrões de Comunicação**: Estatísticas e métricas

### 5. 🌐 Enriquecimento de IPs
- **Geolocalização Automática**: APIs de geolocalização
- **Informações de ISP**: Identificação de provedores
- **Dados Organizacionais**: Informações da organização do IP
- **Cache Inteligente**: Armazenamento local para otimização

## 📁 Estrutura do Projeto

```
corujazap/
├── 📂 app/                          # Aplicação principal
│   ├── main.py                      # Arquivo principal Streamlit
│   └── 📂 pages/                    # Páginas do Streamlit
│       ├── 📂 adm/                  # Módulos administrativos
│       │   ├── config.py            # Configurações de operação
│       │   └── gerenciar_pacotes.py # Upload e gestão de pacotes
│       ├── 📂 arq_dados/            # Análise de dados extraídos
│       │   ├── address_book.py      # Análise de contatos
│       │   └── groups.py            # Análise de grupos
│       ├── 📂 arq_prtt/             # Análise de mensagens
│       │   └── messages.py          # Timeline de mensagens
│       ├── 📂 dashboard/            # Dashboard principal
│       │   └── dashboard.py         # Visão geral da operação
│       └── 📂 ips/                  # Análise de IPs
│           └── geolocations.py      # Mapeamento geográfico
├── 📂 db/                           # Banco de dados
│   ├── init.sql                     # Script de inicialização
│   ├── models.py                    # Modelos SQLAlchemy
│   └── session.py                   # Configuração de sessão
├── 📂 extractor/                    # Extração de dados
│   ├── extractor.py                 # Processador principal
│   └── ip_api_client.py             # Cliente para APIs de IP
├── 📂 data/                         # Dados processados
├── 📄 docker-compose.yaml           # Configuração Docker Compose
├── 📄 Dockerfile                    # Imagem Docker da aplicação
├── 📄 requirements.txt              # Dependências Python
├── 📄 .env                          # Variáveis de ambiente
├── 📄 settings.py                   # Configurações globais
└── 📄 README.md                     # Esta documentação
```

## 🔧 Como Usar

### 1. Primeiro Acesso

1. **Acesse o sistema**:
   - **Docker**: `http://localhost:8501`
   - **Local**: `http://localhost:8501`

2. **Configure uma operação**:
   - Vá em `Administração > Configurações`
   - Crie uma nova operação ou selecione existente

3. **Faça upload dos arquivos**:
   - Vá em `Administração > Gerenciar Pacotes`
   - Faça upload de arquivos `.zip` exportados do WhatsApp

### 2. Análise de Dados

1. **Selecione a operação** ativa na barra lateral
2. **Escolha o módulo** de análise desejado:
   - **Dashboard**: Visão geral
   - **Arq. Dados**: Contatos e grupos
   - **Arq. PRTT**: Mensagens e conversas
   - **IPs**: Geolocalização
3. **Configure os filtros** conforme necessário
4. **Visualize os resultados** em gráficos e mapas

### 3. Geolocalização de IPs

1. **Acesse** `IPs > Geolocalização`
2. **Selecione um telefone** na barra lateral
3. **Defina o período** de análise
4. **Visualize no mapa** com clusters automáticos
5. **Analise estatísticas** geográficas

## 🔗 API e Endpoints

### APIs Externas Utilizadas

- **ip-api.com**: Geolocalização gratuita de IPs
- **OpenStreetMap**: Tiles para mapas interativos


## 🎨 Tecnologias Utilizadas

### Backend
- **Python 3.13**: Linguagem principal
- **SQLAlchemy**: ORM para banco de dados
- **MySQL 8.0**: Banco de dados relacional
- **Pandas**: Manipulação de dados
- **HTTPx**: Requisições HTTP assíncronas

### Frontend
- **Streamlit**: Framework web principal
- **Plotly**: Gráficos interativos
- **Folium**: Mapas interativos
- **Streamlit-Folium**: Integração de mapas

### Infraestrutura
- **Docker**: Containerização da aplicação
- **Docker Compose**: Orquestração de serviços
- **Alpine Linux**: Base da imagem Docker (leve)
- **MySQL**: Banco de dados em container

## 🐛 Solução de Problemas

### Problemas Comuns

#### 1. **Erro de conexão com banco (Docker):**
```bash
# Verificar se containers estão rodando
docker-compose ps

# Verificar logs
docker-compose logs app
docker-compose logs mysql

# Verificar rede
docker network inspect corujazap-net
```

#### 2. **Containers não iniciam:**
```bash
# Recriar containers
docker-compose down
docker-compose up --build -d

# Verificar se a rede existe
docker network create corujazap-net
```

#### 3. **Erro de dependências Python:**
```bash
# Rebuild com cache limpo
docker-compose build --no-cache app
docker-compose up -d
```

#### 4. **Arquivos não são processados:**
- Verifique se o arquivo é um `.zip` válido do WhatsApp
- Confirme que a operação está selecionada
- Verifique logs da aplicação

#### 5. **Mapa não carrega:**
- Verifique conexão com internet
- Confirme se há dados de IPs na operação selecionada

### Comandos de Debug

```bash
# Ver todos os containers
docker ps -a

# Logs em tempo real
docker compose logs -f app

# Entrar no container para debug
docker exec -it corujazap_app sh

# Testar conexão com banco no container
docker exec corujazap_app ping mysql
```

### Reset Completo

```bash
# Parar e remover tudo
docker-compose down -v

# Remover imagens (opcional)
docker rmi corujazap-app mysql:8.0

# Remover rede
docker network rm corujazap-net

# Recriar tudo
docker network create corujazap-net
docker-compose up --build -d
```

### Padrões de Código

- Use **docstrings** em todas as funções
- Siga **PEP 8** para formatação
- Mantenha **compatibilidade** com Docker
- Teste em **ambiente containerizado**

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👨‍💻 Autores

**Dieison Teixeira Soares**
- GitHub: [@di-soares](https://github.com/di-soares)
- Email: dev.dieison@gmail.com

**Rafael Waidemam**
- GitHub: [@rwaidemam](https://github.com/rwaidemam)
- Email: rafaelwaidemam@gmail.com

## 📞 Suporte

Para suporte técnico ou dúvidas:

1. **Verifique a seção** [Solução de Problemas](#-solução-de-problemas)
2. **Consulte os logs** com `docker-compose logs app`
3. **Entre em contato** via email

**Desenvolvido para análise forense digital de pacotes WhatsApp**