# Stage 1: Build
FROM python:3.11.4 as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final Image
FROM python:3.11.4-slim

# Copy built wheels from builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Set work directory
WORKDIR /app

# Copy your application code to the container (make sure .dockerignore is set up)
COPY . .

# Expose port for Gunicorn
EXPOSE 5945

# Create and copy Gunicorn configuration file
COPY gunicorn.conf.py /app/gunicorn.conf.py

# Start Gunicorn with Uvicorn workers
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "service:app"]
