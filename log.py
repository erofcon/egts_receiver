import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger('my_loger')
logger.setLevel(logging.INFO)

file_handler = TimedRotatingFileHandler('logs/log.log', backupCount=100, when='D', interval=1)

file_formatter = logging.Formatter('%(levelname)s | %(asctime)s | %(message)s')
file_handler.setFormatter(file_formatter)

logger.addHandler(file_handler)
