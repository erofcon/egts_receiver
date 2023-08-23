from psycopg2 import connect

cursor = None

try:
    __conn = connect(dbname='road_works_db', user='tm',
                     password='T211sm', host='localhost')
    __conn.autocommit = True
    cursor = __conn.cursor()

except Exception as e:
    raise e


def close_connection():
    if cursor is not None:
        cursor.close()


def get_car_id(imei: str) -> int | None:
    cursor.execute(f"""SELECT * FROM "car" c WHERE c.imei='{imei}' limit 1""")

    for row in cursor:
        return row[0]


def insert_tracker_data(latitude: float, longitude: float, create_datetime: str, car_id: int):
    cursor.execute(
        f'INSERT INTO tracker_data (latitude, longitude, create_datetime, car_id) VALUES {latitude, longitude, create_datetime, car_id}')
