FROM python:3.11-slim

WORKDIR /app

# Instala dependencias primero (aprovecha cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY . .

# Container Apps espera el puerto 8000 por defecto
EXPOSE 8000

# Uvicorn con 2 workers — suficiente para Free Tier
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
