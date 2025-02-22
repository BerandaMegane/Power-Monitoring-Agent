import datetime
import logging
import logging.config
import json
import sys

# サードパーティ
import yaml

file_path = "../log_config.json"
with open(file_path, 'r') as f:
    log_conf = json.load(f)
logging.config.dictConfig(log_conf)
logger = logging.getLogger(__name__)

def logging_sensor_csv(sensor_csv: str):
    """
    sensor_csv を取得時刻とともに記録する
    sensor_csv = "csv-1,60.0,100.0"
    """
    tz_jst = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tz=tz_jst)
    log_record = {
        "sensor": sensor_csv,
        "isotimestamp": dt.isoformat()
    }
    return log_record

def parse_log_record(log_record: dict):
    """
    センサーから送られてきた CSV を解釈する

    log_record: {
        "sensor": sensor_csv,
        "isotimestamp": dt.isoformat()
    }

    return: {
        "mode": "csv-1" or "csv-2"
        "datetime": datetime,
        "isotimestamp": str

        "frequency": float freq,
        "voltage": float voltage,

        "index": int,
        "voltage": float voltage,
    }
    """
    try:
        csv = log_record["sensor"].replace("\n", "").split(",")
        mode = csv[0]
        iso_dt = log_record["isotimestamp"]
        dt = datetime.datetime.fromisoformat(iso_dt)

        if mode == "csv-1" or mode == "csv-2":
            sensor_record = {
                "mode": mode,
                "datetime": dt,
                "isotimestamp": iso_dt,
            }

        if mode == "csv-1":
            sensor_record["frequency"] = float(csv[1])
            sensor_record["voltage"] = float(csv[2])
            return sensor_record
        elif mode == "csv-2":
            sensor_record["index"] = int(csv[1])
            sensor_record["voltage"] = float(csv[2])
            return sensor_record
        else:
            return None
    except:
        # traceback.print_exc()
        return None

# 設定ファイル読み込み
def load_config(file_path):
    try:
        with open(file_path, "r") as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        logger.error(f"The file {file_path} does not exist.")
        sys.exit()
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file. {e}")
        sys.exit()
