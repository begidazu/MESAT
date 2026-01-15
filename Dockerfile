# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1

# WORKDIR /app

# # Dependencias del sistema para stack geoespacial + compilación si hiciera falta

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ca-certificates \
#     gdal-bin \
#     libgdal-dev \
#     proj-bin \
#     libproj-dev \
#     libgeos-dev \
#     libspatialindex-dev \
#     build-essential \
#     libxml2-dev \
#     libxslt1-dev \
#     zlib1g-dev \
#     python3-matplotlib \
#     && rm -rf /var/lib/apt/lists/*

# # (Opcional pero recomendado) actualiza pip para que resuelva wheels mejor
# RUN python -m pip install --upgrade pip

# COPY requirements-docker.txt /app/requirements.txt
# RUN python -m pip install -r /app/requirements.txt

# COPY . /app

# EXPOSE 8050
# CMD ["python", "run.py"]


# ------------------------------ PRODUCTION DOCKERFILE ------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gdal-bin \
    libgdal-dev \
    proj-bin \
    libproj-dev \
    libgeos-dev \
    libspatialindex-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

COPY requirements-docker.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt \
    && python -m pip install gunicorn

COPY . /root


EXPOSE 8050

# Gunicorn WSGI
ENV PORT=8050
## CMD ["gunicorn", "-b", "0.0.0.0:8050","--workers", "4", "--threads", "8", "--timeout", "120", "run:server"]
ENTRYPOINT ["python", "run.py"]



