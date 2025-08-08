import socket
import struct
import time

def get_ntp_time(host='ntp2.aliyun.com'):
    """
    从 NTP 服务器获取当前 Unix 时间戳
    """
    # NTP 时间从 1900 开始，Unix 时间从 1970 开始，相差 70 年
    NTP_DELTA = 2208988800  # 70 years in seconds
    port = 123
    buf = 1024
    address = (host, port)
    msg = b'\x1b' + 47 * b'\0'  # NTP 请求报文

    try:
        # 创建 UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(5)
            s.sendto(msg, address)
            data, _ = s.recvfrom(buf)
        
        # 解包 NTP 响应，取出 Transmit Timestamp（时间戳在第40字节开始，占8字节）
        unpacked = struct.unpack('!12I', data[0:48])
        ntp_time = unpacked[10] + float(unpacked[11]) / 2**32
        unix_time = ntp_time - NTP_DELTA
        return unix_time

    except Exception as e:
        print("NTP 获取失败:", e)
        return None