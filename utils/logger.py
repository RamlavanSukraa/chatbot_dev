# utils/logger.py

import logging

def setup_logger(name, level=logging.INFO):
    """
    Set up a logger with the specified name and level.
    Logs messages to the console with a specific format.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()  # Create a console handler
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.hasHandlers():
        logger.addHandler(console_handler)

    return logger

# Pre-configured logger instance for the application
app_logger = setup_logger('app_logger', level=logging.DEBUG)
app_logger.info('Logger initialized')
