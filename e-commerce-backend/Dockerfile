FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install whitenoise gunicorn

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p staticfiles media logs

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create a startup script
RUN echo '#!/bin/bash\n\
echo "Starting Nexus E-commerce Platform..."\n\
echo "Running database migrations..."\n\
python manage.py migrate --noinput\n\
echo "Migrations complete!"\n\
echo "Starting Gunicorn server..."\n\
exec gunicorn nexus.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --access-logfile - --error-logfile -\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port 
EXPOSE 8000

# Start the application
CMD ["/app/start.sh"]