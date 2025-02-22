#!/usr/bin/env python3

"""
main.py へ接続するクライアントとして動作する。
"""

import sys
import asyncio

# 自作
sys.path.append("../")
import common.utility

# 設定ファイル読み込み
config = common.utility.load_config("../config.yaml")

async def tcp_echo_client():
  reader, writer = await asyncio.open_connection(
    config["grid-power-adapter"]["client"]["host"],
    config["grid-power-adapter"]["client"]["port"],
  )

  while data := await reader.read(1024):
    data = data.decode().replace("\n", "")
    print('Received:', data)

asyncio.run(tcp_echo_client())
