from datetime import datetime

import crcmod

from . import egts_constants

crc8_func = crcmod.mkCrcFun(0x0131, initCrc=0xFF, rev=False)
crc16_func = crcmod.mkCrcFun(0x011021, initCrc=0xFFFF, rev=False)


class EgtsProtocol:
    __buff: bytes

    # EGTS Transport Layer
    protocol_version: int
    flags: int
    prefix: int
    header_length: int
    frame_data_length: int
    packet_identifier: int
    packet_type: int
    header_check_sum: int

    # Service Layer Record
    services_frame_data: bytes

    # Response
    records: list
    __response: bytes

    def __init__(self, buff):
        self.__buff = buff
        self.records = []
        self.__run_parse()

    def __run_parse(self):
        try:
            self.protocol_version = self.__buff[0]
            self.flags = self.__buff[2]
            self.prefix = self.__buff[2] >> 6
            self.header_length = self.__buff[3]
            self.frame_data_length = int.from_bytes(self.__buff[5:7], byteorder='little')
            self.packet_identifier = int.from_bytes(self.__buff[7:9], byteorder='little')
            self.packet_type = self.__buff[9]
            self.header_check_sum = self.__buff[self.header_length - 1]

            crc8_checksum = crc8_func(self.__buff[:self.header_length - 1])

            if self.protocol_version != egts_constants.EGTS_PROTOCOL_VERSION:
                raise "Error! EGTS_PC_UNS_PROTOCOL неподдерживаемый протокол"

            if self.prefix != egts_constants.PREFIX_NUMBER:
                raise "Error! EGTS_PC_UNS_PROTOCOL неподдерживаемый протокол"

            if 10 > self.header_length > 17:
                raise "Error! EGTS_PC_INC_HEADERFORM неверный формат заголовка"

            if self.header_check_sum != self.header_check_sum != crc8_checksum:
                raise "Error! EGTS_PC_HEADERCRC_ERROR ошибка контрольной суммы заголовка"

            self.__service_layer_record_parse(buff=self.__buff[self.header_length:])
        except Exception:
            pass

    def __service_layer_record_parse(self, buff):
        self.services_frame_data = buff[:self.frame_data_length]

        if self.packet_type == egts_constants.EGTS_PT_APPDATA:
            self.__appdata_parse()
        elif self.packet_type == egts_constants.EGTS_PT_RESPONSE:
            self.__response_parse()

    def __appdata_parse(self):

        rest_buf = self.services_frame_data

        while len(rest_buf) > 0:
            result = EgtsRecord(buff=rest_buf).parse()
            self.records.append(result)
            rest_buf = rest_buf[result['rec_length']:]

        if self.records:
            self.service = self.records[0]['source_service_type']

    def __response_parse(self):
        rest_buf = self.services_frame_data[3:]
        self.records = []
        while len(rest_buf) > 0:
            result = EgtsRecord(buff=rest_buf).parse()
            self.records.append(result)
            rest_buf = rest_buf[result['rec_length']:]

        if self.records:
            self.service = self.records[0]['source_service_type']

    @staticmethod
    def _make_record(service, ans_rid, subrecords):
        sub_len = len(subrecords).to_bytes(2, 'little')
        rid = ans_rid.to_bytes(2, 'little')
        body = sub_len + rid + b'\x18' + service.to_bytes(1, 'little') + service.to_bytes(1, 'little') + subrecords
        return body

    @staticmethod
    def _make_header(ans_pid, data_len, type):
        rec_len = data_len.to_bytes(2, 'little')
        ans_rid_bin = ans_pid.to_bytes(2, 'little')
        header = b'\x01\x00\x03\x0b\x00' + rec_len + ans_rid_bin + type.to_bytes(1, 'little')
        return header

    @staticmethod
    def _packet_bin(ans_pid, body, type):
        bcs = crc16_func(body)
        data_len = len(body)
        header = EgtsProtocol._make_header(ans_pid, data_len, type)
        hcs = crc8_func(header)
        bcs_bin = bcs.to_bytes(2, 'little')
        reply = header + hcs.to_bytes(1, 'little') + body + bcs_bin
        return reply

    def reply(self, package_id, answer_id):
        subrecords = self._reply_record()
        pack_id = self.packet_identifier.to_bytes(2, 'little')
        body = pack_id + b'\x00' + self._make_record(self.service, answer_id, subrecords)

        reply = self._packet_bin(package_id, body, 0)
        return reply

    def _reply_record(self):
        res = b""
        for record in self.records:
            rec_id = record['record_number']
            reply_subrec = bytes([0x00, 0x03, 0x00, rec_id % 256, rec_id // 256, 0])
            res += reply_subrec
        return res


class EgtsRecord:
    __record_data: bytes
    __source_service_type: int

    def __init__(self, buff):
        self.__buff = buff

    def parse(self):
        record_length = int.from_bytes(self.__buff[:2], byteorder='little')
        record_number = int.from_bytes(self.__buff[2:4], byteorder='little')

        tmfe = self.__buff[4] >> 2 & 1
        evfe = self.__buff[4] >> 1 & 1
        obfe = self.__buff[4] & 1

        opt_len = (tmfe + evfe + obfe) * 4

        source_service_type = self.__buff[5 + opt_len]

        self.__record_data = self.__buff[7 + opt_len:]

        header_len = egts_constants.EGTS_SERVICE_LAYER_MIN_RECORD_HEADER_LEN + opt_len

        rec_length = record_length + header_len

        rd = self.__record_data
        subrecords = []
        while len(rd) > 0:
            sr_subrecord = self.__parse_subrecord_data(buff=rd)
            subrecords.append(sr_subrecord)
            rd = rd[sr_subrecord['subrecord_length']:]

        return {'rec_length': rec_length, 'record_number': record_number, 'source_service_type': source_service_type,
                'subrecords': subrecords}

    @staticmethod
    def __parse_subrecord_data(buff):
        subrecord_type = buff[0]
        subrecord_length = int.from_bytes(buff[1:3], byteorder='little')

        subrecord_data = buff[3:]

        # EGTS_SR_POS_DATA
        if subrecord_type == 16:
            navigation_time = (int.from_bytes(subrecord_data[:4],
                                              byteorder='little') + egts_constants.timestamp_20100101_000000_utc)
            lohs = subrecord_data[12] >> 6 & 1
            lahs = subrecord_data[12] >> 5 & 1

            latitude = (int.from_bytes(subrecord_data[4:8], byteorder='little') * 90 / 0xffffffff) * (1 - 2 * lahs)
            longitude = (int.from_bytes(subrecord_data[8:12], byteorder='little') * 180 / 0xffffffff) * (1 - 2 * lohs)
            time = datetime.fromtimestamp(navigation_time)

            return {'subrecord_type': subrecord_type, 'subrecord_length': 3 + subrecord_length, 'latitude': latitude,
                    'longitude': longitude, 'navigation_time': str(time)}

        # EGTS_SR_TERM_IDENTITY
        elif subrecord_type == 1:
            hdide = subrecord_data[4] & 1

            if hdide != 0:
                imei = subrecord_data[7:22]
            else:
                imei = subrecord_data[5:20]

            return {'subrecord_type': subrecord_type, 'subrecord_length': 3 + subrecord_length, 'imei': imei}

        return {'subrecord_type': subrecord_type, 'subrecord_length': 3 + subrecord_length}
