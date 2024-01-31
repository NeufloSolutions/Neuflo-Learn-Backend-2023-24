# Use an official Python runtime as a base image
FROM python:3.11.4

# Set environment variables to reduce Python bytecode generation and buffer flushing
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/

# Expose the port the app runs on
EXPOSE 5945

# Define the command to run your app
CMD ["gunicorn", "--bind", "0.0.0.0:5945", "-k", "uvicorn.workers.UvicornWorker", "service:app"]
