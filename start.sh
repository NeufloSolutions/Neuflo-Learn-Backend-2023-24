#!/bin/bash

echo "Starting the start.sh script..."

# Start Redis server
redis-server /etc/redis/redis.conf --daemonize yes

echo "Redis server started."

# Start your Python application
exec gunicorn --bind localhost:5912 -k uvicorn.workers.UvicornWorker service:app
