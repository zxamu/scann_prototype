FROM python:3.11-bullseye

# 1. Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    python3-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Configurar el entorno
WORKDIR /app
ENV PYTHONPATH=/app
ENV PATH="/root/.local/bin:${PATH}"

# 3. Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir gunicorn && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copiar la aplicación
COPY . .

# 5. Verificar instalación (para diagnóstico)
RUN which gunicorn && gunicorn --version

# 6. Ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]