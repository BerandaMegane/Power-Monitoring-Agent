#!/usr/bin/env python3

"""
シリアル通信で電源周波数測定センサへ接続する。
サーバとして動作し、他プログラムからの接続を受け付ける。
"""

import asyncio
import json
import logging
import logging.config
import sys
import threading
import time
import traceback

# サードパーティ
import serial
from serial.tools import list_ports

# 自作
sys.path.append("../")
import common.utility
from common.signal_handling import TerminatedException, set_signal_handling

# ログ
file_path = "../log_config.json"
with open(file_path, 'r') as f:
    log_conf = json.load(f)
logging.config.dictConfig(log_conf)
logger = logging.getLogger(__name__)
logger.info("logger start")

# 設定ファイル読み込み
config = common.utility.load_config("../config.yaml")

# シリアル通信ポート選択
def connect_serial() -> serial.Serial | None:
    ser = serial.Serial()
    ser.baudrate = 19200
    ser.timeout = 1

    # 接続可能なデバイス名
    white_list = [
        "COM6",
        "/dev/ttyUSB0",
        "/dev/ttyACM0",  # Ubuntu, Serial-USBアダプタ使用
    ]

    found_devices = [info.device for info in list_ports.comports()]

    logger.info("シリアル接続可能ポートを表示します")
    
    for i in range(len(found_devices)):
        logger.info("%d: %s" % (i, found_devices[i]))

    for device in white_list:
        if device in found_devices:
            ser.port = device
            
            # 試しに接続してみて、成功したら返す
            try:
                ser.open()

                if ser.is_open:
                    logger.info(ser.port + " への接続に成功しました")
                    return ser

            except:
                traceback.print_exc()

                ser.close()
                pass

            if not ser.is_open:
                continue
    
    # 失敗したら None を返す
    return None

class SensorServer:
    def __init__(self) -> None:
        self.conns = set()
        self.is_stop = False

    def serial_recv_proc(self) -> None:
        """
        周波数測定センサへシリアル接続する処理
        """
        logger.info("スレッド開始: 周波数測定アダプタ シリアル通信")
        while not self.is_stop:
            ser = connect_serial()

            if ser is None or not ser.is_open:
                logger.info("シリアル接続に失敗したため、10秒後に再試行します")
                time.sleep(10)
                continue

            try:
                # バッファクリア
                ser.reset_input_buffer()
                while not self.is_stop:
                    # 1行取得
                    """
                    mode, freq, voltage
                    csv-1,60.015,117.86
                    """
                    line = ser.readline().decode().replace("\n", "")
                    logger.debug("> {}".format(line))
                    
                    # クライアントへ送信
                    record = common.utility.logging_sensor_csv(line)
                    self.send_all_clients(json.dumps(record))
            except:
                traceback.print_exc()
            finally:
                ser.close()

        # スレッド終了時
        logger.info("スレッド終了: 周波数測定アダプタ シリアル通信")

    def socket_server_proc(self) -> None:
        """
        ソケット接続を受け付けるスレッド
        """
        logger.info("スレッド開始: ソケット通信 サーバ")
        try:
            asyncio.run(self.run_socket_server())
        except:
            traceback.print_exc()
        finally:
            # スレッド終了時
            logger.info("スレッド終了: ソケット通信 サーバ")

    async def run_socket_server(self):
        """
        ソケット通信サーバ
        """
        self.server_socket = await asyncio.start_server(
            self.handle_client,
            config["grid-power-adapter"]["server"]["host"],
            config["grid-power-adapter"]["server"]["port"],
        )
        await self.server_socket.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        接続クライアントごとの処理
        """
        try:
            self.conns.add(writer)
            logger.info("クライアントを追加しました")
            while not writer.is_closing() and not self.is_stop:
                await asyncio.sleep(1)
        # except asyncio.CancelledError:
        #     logger.info("stoped. asyncio.CancelledError")
        except:
            traceback.print_exc()
        finally:
            self.conns.remove(writer)
            logger.info("クライアントを削除しました")

    def send_all_clients(self, data: str):
        try:
            for writer in self.conns:
                writer.write((data + "\n").encode())
        except:
            traceback.print_exc()
            pass

    def stop(self):
        self.is_stop = True
        self.server_socket.close()

if __name__ == "__main__":
    # SIGNAL を適切に処理する
    set_signal_handling()
    server = SensorServer()

    # シリアル通信 受信スレッド
    serial_recv_thread = threading.Thread(target=server.serial_recv_proc)
    serial_recv_thread.start()

    # TCP Server スレッド
    socket_server_thread = threading.Thread(target=server.socket_server_proc)
    socket_server_thread.start()

    try:
        socket_server_thread.join()
    except KeyboardInterrupt:
        server.stop()
        print("KeyboardInterrupt: stopped by keyboard input (ctrl-C)")
    except TerminatedException:
        server.stop()
        print("TerminatedExecption: stopped by systemd")
    except Exception as e:
        server.stop()
        print("UNKNOWN_ERROR")
        traceback.print_exc()
        raise e
    finally:
        server.stop()
