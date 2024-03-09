LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# In your main app module
import logging
from logging.config import dictConfig
from .logging_config import LOGGING_CONFIG

dictConfig(LOGGING_CONFIG)
