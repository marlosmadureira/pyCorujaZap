FROM python:3.13-alpine

WORKDIR /corujazap

# Instalar dependências do sistema necessárias para compilação
RUN apk add --no-cache gcc musl-dev mariadb-connector-c-dev pkgconfig build-base

# Copiar arquivo de requirements (se existir) ou instalar diretamente
COPY requirements.txt /corujazap

# Instalar dependências Python
RUN pip install -r requirements.txt

# Copiar código da aplicação
COPY . /corujazap

# Expor porta para Streamlit
EXPOSE 8501

# Mapeamento de volumes
VOLUME /corujazap

# Comando padrão para Streamlit
CMD ["streamlit", "run", "app/main.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
