import socket
from _thread import *

from egts.egts_protocol import EgtsProtocol
from egts.egts_constants import EGTS_MIN_TRANSPORT_LENGTH
from db import get_car_id, insert_tracker_data
from loguru import logger


def handler(connection):
    package_id = 0
    answer_id = 0
    imei = ''
    car_id = None

    try:
        while True:
            data = connection.recv(1024).strip()
            try:
                if len(data) >= EGTS_MIN_TRANSPORT_LENGTH:
                    egts = EgtsProtocol(buff=data)
                    if egts.records:
                        for i in egts.records:
                            for sub in i['subrecords']:
                                if sub['subrecord_type'] == 1:
                                    logger.info(sub)
                                    imei = sub['imei'].decode()
                                    if imei != '':
                                        car_id = get_car_id(imei=imei)

                                elif sub['subrecord_type'] == 16:
                                    if not car_id:
                                        car_id = get_car_id(imei=imei)

                                    if car_id:
                                        insert_tracker_data(latitude=sub['latitude'], longitude=sub['longitude'],
                                                            create_datetime=sub['navigation_time'], car_id=car_id)
                                        logger.info(f'{sub} {imei}')
                                    else:
                                        logger.info(f'Unregistered device ', {imei})

                        connection.sendall(egts.reply(package_id=package_id, answer_id=answer_id))
                        package_id += 1
                        answer_id += 1

            except Exception as e:
                logger.error(e)
    finally:
        connection.close()


def accept_connections(server_socket: socket.socket):
    client, address = server_socket.accept()
    logger.info('Connected to: ' + address[0] + ':' + str(address[1]))
    start_new_thread(handler, (client,))


def start_server(host: str, port: int):
    server_socket = socket.socket()

    try:
        server_socket.bind((host, port))
        print(f'Server is listing on the port {port}...')
        logger.info(f'Server is listing on the port {port}...')
        server_socket.listen()

        while True:
            accept_connections(server_socket)

    except socket.error as e:
        logger.error(str(e))

    finally:
        logger.info(f'Server listing on the port {port}...')
        server_socket.close()
