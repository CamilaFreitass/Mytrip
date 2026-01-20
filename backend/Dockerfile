# Usa imagem Python oficial leve
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os requisitos e instala
# (O gunicorn deve estar no requirements.txt conforme conversamos)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo da pasta backend para dentro do container
COPY . .

# Variável de ambiente para garantir que os logs apareçam imediatamente
ENV PYTHONUNBUFFERED=1

# Expõe a porta 5000 (padrão do seu backend Flask)
EXPOSE 5000

# Comando para rodar com Gunicorn em produção
# 'main:app' significa: procure o objeto 'app' dentro do arquivo 'main.py'
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app