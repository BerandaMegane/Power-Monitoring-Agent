#!/usr/bin/env python3
import asyncio
import json
import logging
import logging.config
import os
import sys
import time
import traceback

# サードパーティ
import ambient

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
    
# プロキシ設定
if "proxy" in config["thingsboard-agent"]:
    os.environ['HTTP_PROXY'] = config["thingsboard-agent"]["proxy"]["http_proxy"]
    os.environ['HTTPS_PROXY'] = config["thingsboard-agent"]["proxy"]["https_proxy"]
    os.environ['NO_PROXY'] = config["thingsboard-agent"]["proxy"]["no_proxy"]

class AmbientSendAgent:
    AMBIENT_SEND_CYCLE = 60

    def __init__(self) -> None:
        self.is_stop = False
        self.record_buffer = list()

        self._restart_time = 10

    async def ambient_send_proc(self):
        while not self.is_stop:
            try:
                logger.info("Grid Power Adapter へ接続開始")
                reader, writer = await asyncio.open_connection(
                    config["grid-power-adapter"]["client"]["host"],
                    config["grid-power-adapter"]["client"]["port"],
                )
                logger.info("Grid Power Adapter 接続完了")

                self.reader = reader
                self.writer = writer
                while jsondata := await reader.read(1024):
                    jsondata = jsondata.decode().replace("\n", "")
                    logger.debug('Received: %s' % jsondata)
                    sensor_record = common.utility.parse_log_record(json.loads(jsondata))

                    if sensor_record is not None and sensor_record["mode"] == "csv-1":
                        self.load_sensor_record(sensor_record)
                        self.send_ambient()

            except ConnectionRefusedError:
                if not self.is_stop:
                    self._restart_time = 30
                    logger.info("ConnectionRefusedError: %d秒後に再接続を試みます" % self._restart_time)
                    time.sleep(self._restart_time)
            except Exception as e:
                traceback.print_exc()
                if not self.is_stop:
                    raise e

    def load_sensor_record(self, sensor_record: dict):
        self.record_buffer.append(sensor_record)

    def send_ambient(self):
        # AMBIENT_SEND_CYCLE回に1回送信する
        if len(self.record_buffer) >= AmbientSendAgent.AMBIENT_SEND_CYCLE:
            # 必要データを取得
            records = self.record_buffer[ : AmbientSendAgent.AMBIENT_SEND_CYCLE]
            self.record_buffer = self.record_buffer[AmbientSendAgent.AMBIENT_SEND_CYCLE : ]

            freq = sum([x["frequency"] for x in records]) / AmbientSendAgent.AMBIENT_SEND_CYCLE
            voltage = sum([x["voltage"] for x in records]) / AmbientSendAgent.AMBIENT_SEND_CYCLE
            created_time = records[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            
            data = {
                "d1": freq,
                "d2": voltage,
                "created": created_time,
            }
            
            am = ambient.Ambient(
                config["ambient-agent"]["channel_id"],
                config["ambient-agent"]["write_key"],
                userKey=config["ambient-agent"]["user_key"],
            )
            res = am.send(data)
            logger.debug("Ambient send: {} {} {} {}".format(res.status_code, created_time, freq, voltage))

    def stop(self):
        self.is_stop = False

if __name__ == "__main__":
    # SIGNAL を適切に処理する
    set_signal_handling()
    
    # Agent
    agent = AmbientSendAgent()

    try:
        asyncio.run(agent.ambient_send_proc())
    except KeyboardInterrupt:
        agent.stop()
        logger.info(" KeyboardInterrupt: stopped by keyboard input (ctrl-C)")
    except TerminatedException:
        agent.stop()
        logger.info(" TerminatedExecption: stopped by systemd")
    except Exception as e:
        agent.stop()
        logger.warning(str(e))
        # program will be restarted automatically by systemd (Restart on-failure)
        raise e
    finally:
        agent.stop()
