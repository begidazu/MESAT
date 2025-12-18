FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Paquetes del sistema (añade más si alguna lib lo pide)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# 1) Copiamos requirements
COPY requirements.txt /app/requirements.txt

# 2) Copiamos wheels (si existe) para instalaciones offline/fiables (GDAL, etc.)
COPY wheels/ /wheels/

# 3) Instalamos deps usando wheels como fuente adicional
RUN pip install --no-cache-dir --find-links=/wheels -r /app/requirements.txt

# 4) Copiamos el código
COPY . /app

EXPOSE 8050

CMD ["python", "run.py"]
