# Usa uma imagem leve do Python
FROM python:3.11-slim
# Define a pasta de trabalho dentro do container
WORKDIR /app
# Copia os arquivos de requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Instala o servidor de produção Gunicorn
RUN pip install gunicorn
# Copia todo o restante do código para dentro do container
COPY . .
# Comando para rodar a aplicação usando Gunicorn
# "trip:app" significa: pacote "trip", objeto "app" (que está no __init__.py)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 trip:app