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
import requests

# 自作
sys.path.append("../")
import common.utility
from common.signal_handling import TerminatedException, set_signal_handling

# ログ
with open('../log_config.json', 'r') as f:
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

class ThingsBoardAgent:
    def __init__(self) -> None:
        self.is_stop = False

    async def send_proc(self):
        while not self.is_stop:
            try:
                logger.info("Grid Power Adapter へ接続開始")
                reader, writer = await asyncio.open_connection(
                    config["grid-power-adapter"]["client"]["host"],
                    config["grid-power-adapter"]["client"]["port"]
                )
                logger.info("Grid Power Adapter 接続完了")

                self.reader = reader
                self.writer = writer
                while recvdata := await reader.read(1024):
                    try:
                        jsondata = json.loads(recvdata.decode())
                        logger.debug('Received: %s' % jsondata)
                    except json.decoder.JSONDecodeError:
                        continue
                    
                    sensor_record = common.utility.parse_log_record(jsondata)
                    if sensor_record is not None and sensor_record["mode"] == "csv-1":
                        self.send_thingsboard(sensor_record)

            except ConnectionRefusedError:
                if not self.is_stop:
                    self._restart_time = 30
                    logger.info("ConnectionRefusedError: %d秒後に再接続を試みます" % self._restart_time)
                    time.sleep(self._restart_time)
            except OSError:
                if not self.is_stop:
                    self._restart_time = 30
                    logger.info("OSError: %d秒後に再接続を試みます" % self._restart_time)
                    time.sleep(self._restart_time)
            except Exception as e:
                logger.exception()
                if not self.is_stop:
                    logger.info("Unknown Error: %d秒後に再接続を試みます" % self._restart_time)
                    time.sleep(self._restart_time)

    def send_thingsboard(self, record):
        # 必要データを取得
        keep_keys = {"frequency", "voltage"}
        filtered_data = {k: record[k] for k in keep_keys}

        logger.debug(str(filtered_data))

        # 送信
        headers = { "Content-Type": "application/json" }
        res = requests.post(
            config["thingsboard-agent"]["url"],
            headers=headers, 
            data=json.dumps(filtered_data),
        )

        logger.debug("ThingsBoard send: {} {}".format(res.status_code, res))

    def stop(self):
        self.is_stop = False

if __name__ == "__main__":
    # SIGNAL を適切に処理する
    set_signal_handling()
    
    # Agent
    agent = ThingsBoardAgent()

    try:
        asyncio.run(agent.send_proc())
    except KeyboardInterrupt:
        agent.stop()
        logger.info(" KeyboardInterrupt: stopped by keyboard input (ctrl-C)")
    except TerminatedException:
        agent.stop()
        logger.info(" TerminatedExecption: stopped by systemd")
    except Exception as e:
        agent.stop()
        logger.exception(" Unknown Error")
        # program will be restarted automatically by systemd (Restart on-failure)
        raise e
    finally:
        agent.stop()
