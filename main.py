import argparse
import atexit

from loguru import logger

from db import cursor, close_connection
from server import start_server

logger.add("/mnt/projects_files/egts_receiver/logs/log.log", rotation="00:00")

parser = argparse.ArgumentParser()

parser.add_argument('--port', default=6543, help='listening port')
parser.add_argument('--hostname', default='', help='hostname')

arg = parser.parse_args()

atexit.register(close_connection)

if __name__ == '__main__':
    if cursor is None:
        raise Exception
    start_server(host=arg.hostname, port=arg.port)
