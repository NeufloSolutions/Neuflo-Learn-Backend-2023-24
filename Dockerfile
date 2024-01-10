# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.4

EXPOSE 4567

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Install additional packages needed for Redis
RUN apt-get update && \
    apt-get install -y lsb-release curl gpg && \
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list && \
    apt-get update && \
    apt-get install -y redis redis-tools && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Copy and make the start script executable
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Set the start script as the entry point
CMD ["/start.sh"]
