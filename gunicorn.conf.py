import os

# Basic server settings
bind = "0.0.0.0:5945"
workers = 2  # Adjust based on your environment
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120

# Logging
accesslog = "-"  # Use "-" for stdout
errorlog = "-"  # Use "-" for stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'