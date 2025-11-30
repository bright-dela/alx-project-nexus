FROM python:3.12-slim 

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Start server with dynamic Railway port
CMD ["sh", "-c", "gunicorn e-commerce-backend.nexus.wsgi:application --bind 0.0.0.0:${PORT}"]
