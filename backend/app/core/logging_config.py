import logging
import sys
from datetime import datetime

# configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'/var/log/trickyclip/app_{datetime.now().strftime("%Y%m%d")}.log', mode='a')
    ]
)

def get_logger(name: str) -> logging.Logger:
    """get a configured logger instance"""
    return logging.getLogger(name)

# create logs directory if it doesn't exist
import os
os.makedirs('/var/log/trickyclip', exist_ok=True)

