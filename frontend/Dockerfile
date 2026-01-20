# Usa uma imagem Python leve
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia requisitos
COPY requirements.txt .

# Instala dependências e Gunicorn
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# Copia o restante do código do frontend (incluindo templates e static)
COPY . .

# Expõe a porta 8080 (padrão do Cloud Run)
EXPOSE 8080

# Comando otimizado para Cloud Run
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main_front:app