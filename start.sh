#!/bin/bash

# Script de start para Render
# Lê a variável PORT do ambiente (Render define automaticamente)
# Se não estiver definida, usa 8000 como padrão

PORT=${PORT:-8000}

echo "Starting server on port $PORT"

# Executar migrações antes de iniciar
python manage.py migrate --noinput

# Iniciar gunicorn
exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    zapsign_project.wsgi:application

