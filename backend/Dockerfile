# Base image
FROM public.ecr.aws/docker/library/python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libpangocairo-1.0-0 \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy custom fonts
COPY static/fonts/JameelNooriNastaleeq.ttf /usr/share/fonts/truetype/JameelNooriNastaleeq.ttf
RUN fc-cache -f -v

# Copy project
COPY . /app/

# Make entrypoint executable and ensure LF line endings
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Environment variables for collectstatic
ENV SECRET_KEY=collectstatic-dummy-key
ENV DEBUG=False

# Collect static files
RUN python manage.py collectstatic --noinput

# Port for Django
EXPOSE 8000

# Default command: use entrypoint (runs migrations + superuser + gunicorn)
CMD ["/app/entrypoint.sh"]
