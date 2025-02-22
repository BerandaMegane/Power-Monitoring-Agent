# Power-Monitoring-Agent

[自作の電源周波数測定アダプタ](https://github.com/BerandaMegane/Commercial-Power-Measurement-Adapter) からシリアル経由で送られてくる電源周波数情報を取得し、可視化サービス（Ambient, ThingsBoard）へ送信するプログラム。

動作確認している環境は次のとおりです。
* Ubuntu, Raspberry Pi OS
* Python 3.10
* venv

使用している主なソフトウェア・ライブラリ等は次のとおりです。
* [ambient-python-lib](https://github.com/AmbientDataInc/ambient-python-lib)
* [pyserial](https://github.com/pyserial/pyserial)
* [pyyaml](https://pyyaml.org/)

## 概要
### 1: 電源周波数測定アダプタ - grid-power-adapter
自作測定器からシリアル通信で送られてきてくるデータを取得します。  
TCP 通信のサーバとなり `127.0.0.1:12345` へ接続することで、他ソフトウェアからデータを利用できるようにします。

### 2: Ambient エージェント - ambient-agent
自作測定器で取得したデータを Ambient へ送信します。  
送信したデータは、次のサイトで眺めることができます。
* [Ambient - 電源周波数（中国電力・岡山市自宅）](https://ambidata.io/bd/board.html?id=25449)

### 3: ThingsBoard エージェント - thingsboard-agent
自作測定器で取得したデータを ThingsBoard へ送信します。  
送信したデータは、次のサイトで眺めることができます。ただし、自宅サーバで運営しているため、閲覧できないこともあります。
* [ThingsBoard - 商用電源変動モニタ](https://iot.bocchi-megane.dev/dashboard/5340d990-d59f-11ef-bc08-75445bf1bc79?publicId=4a2f1750-d607-11ef-9ecb-8d8fd3f8b9fe)

## 使用方法

### 0: 環境構築
Debian 系 OS の場合は、apt で必要なパッケージをインストールしてください。
```bash
sudo apt install python3 python3-venv python3-pip
```

### 1: インストール
初めて使用するときは、使用しているライブラリのインストールを行います。  
ここでは venv を使用しています。（使用しなくても問題はありません）

```bash
# リポジトリコピー
git clone https://github.com/BerandaMegane/Power-Monitoring-Agent.git
cd Power-Monitoring-Agent
# venv 環境構築
python -m venv venv
# venv アクティベート
source ./venv/bin/activate
# 推奨ライブラリのインストール (requirements.txt 使用)
pip install -r requirements.txt
# secret.py の作成と編集
cp config-sample.yaml config.yaml
vi config.yaml
```

### 2: シリアル通信の許可 (Ubuntu, Raspberry Pi OS)
ユーザがシリアル通信できるよう、dialoutグループに所属させます。
```bash
sudo usermod -aG dialout $USER
```

### 3: 電源周波数測定アダプタ
venv を使用している場合は、アクティベートしてから実行します。  
とりあえず一時的に実行してみます。
```bash
cd grid-power-adapter
python main.py
```

一時的に実効してみて問題なければ、service ファイルを設置・編集します。  
service ファイル内の WorkingDirectory と ExecStart を変更します。
```bash
sudo cp grid-power-adapter.service.template /etc/systemd/system/grid-power-adapter.service
sudo vi /etc/systemd/system/grid-power-adapter.service
```

systemd で実行・永続化します。
```bash
# リロード
sudo systemctl daemon-reload
# 起動
sudo systemctl start grid-power-adapter.service
# 自動起動
sudo systemctl enable grid-power-adapter.service
# 確認
systemctl status grid-power-adapter.service
```

### 4: Ambient 送信
venv を使用している場合は、アクティベートしてから実行します。  
とりあえず一時的に実行してみます。
```bash
# Ambient 送信
cd ambient-agent
python main.py
```

一時的に実効してみて問題なければ、service ファイルを設置・編集します。  
service ファイル内の WorkingDirectory と ExecStart を変更します。
```bash
sudo cp ambient-agent.service.template /etc/systemd/system/ambient-agent.service
sudo vi /etc/systemd/system/ambient-agent.service
```

systemd で実行・永続化します。
```bash
# リロード
sudo systemctl daemon-reload
# 起動
sudo systemctl start ambient-agent.service
# 自動起動
sudo systemctl enable ambient-agent.service
# 確認
systemctl status ambient-agent.service
```

### 5: ThingsBoard 送信
venv を使用している場合は、アクティベートしてから実行します。  
とりあえず一時的に実行してみます。
```bash
# ThingsBoard 送信
cd thingsboard-agent
python main.py
```

一時的に実効してみて問題なければ、service ファイルを設置・編集します。  
service ファイル内の WorkingDirectory と ExecStart を変更します。
```bash
sudo cp thingsboard-agent.service.template /etc/systemd/system/thingsboard-agent.service
sudo vi /etc/systemd/system/thingsboard-agent.service
```

systemd で実行・永続化します。
```bash
# リロード
sudo systemctl daemon-reload
# 起動
sudo systemctl start thingsboard-agent.service
# 自動起動
sudo systemctl enable thingsboard-agent.service
# 確認
systemctl status thingsboard-agent.service
```

## 備忘録
```bash
# ライブラリ更新
pip-review --auto
# requirements.txt の更新
pip freeze > requirements.txt
```
