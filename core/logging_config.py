import sys
import logging

# Configure logging
logging.basicConfig(
    filename=f'{sys.argv[0]}/../app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger
logger = logging.getLogger(__name__)
