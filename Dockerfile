# 1. Usamos una imagen ligera oficial de Python basada en Alpine Linux para optimizar espacio en la Raspberry
FROM python:3.9-slim

# 2. Establecer variables de entorno para evitar que Python escriba archivos .pyc y asegurar logs inmediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Crear y definir el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Instalar dependencias del sistema necesarias para compilar o gestionar paquetes (si hiciera falta)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar el archivo de requerimientos primero para aprovechar la caché de capas de Docker
COPY requirements.txt .

# 6. Instalar todas las dependencias de Python listadas
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copiar el resto del código fuente de nuestra aplicación al contenedor
COPY . .

# 8. Exponer el puerto por el que escuchará FastAPI (por defecto el 8000)
EXPOSE 8000

# 9. Comando definitivo para arrancar la app con Uvicorn de forma pública (0.0.0.0)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]