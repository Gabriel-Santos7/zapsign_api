FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN mkdir -p /app/logs

# Tornar o script de start executável
RUN chmod +x /app/start.sh

# Expor porta dinâmica (Render usa variável PORT, padrão 8000)
EXPOSE 8000

# Usar script de start que lê a variável PORT do ambiente
CMD ["/app/start.sh"]

