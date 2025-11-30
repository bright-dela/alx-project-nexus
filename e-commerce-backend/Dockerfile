FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Hard-coded internal port for Railway
EXPOSE 8000

CMD ["gunicorn", "nexus.wsgi:application", "--bind", "0.0.0.0:8000"]
