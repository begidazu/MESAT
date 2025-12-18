FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# GDAL y dependencias del sistema (Linux)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gdal-bin \
    libgdal-dev \
    proj-bin \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8050
CMD ["python", "run.py"]

