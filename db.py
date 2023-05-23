from psycopg2 import connect

cursor = None

try:
    __conn = connect(dbname='test_db', user='user',
                     password='qwerty123', host='localhost')
    __conn.autocommit = True
    cursor = __conn.cursor()

except Exception as e:
    raise e


def close_connection():
    if cursor is not None:
        cursor.close()


def get_imei_id(imei: str) -> int | None:
    cursor.execute(f"SELECT * FROM car_data c WHERE c.imei='{imei}' limit 1")

    for row in cursor:
        return row[0]


def insert_tracker_data(latitude: float, longitude: float, create_datetime: str, imei_id: int):
    cursor.execute(
        f'INSERT INTO tracker_data (latitude, longitude, create_datetime, imei_id) VALUES {latitude, longitude, create_datetime, imei_id}')
