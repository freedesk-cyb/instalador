# Usar una imagen de Python ligera
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del servidor y la base de datos (si existe)
COPY server.py .
# Nota: La base de datos assets.db se manejará preferiblemente mediante volúmenes en docker-compose,
# pero copiamos el archivo inicial si existe.
COPY assets.db* .

# Exponer el puerto que usa Flask
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["python", "server.py"]
