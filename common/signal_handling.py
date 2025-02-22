# 公式
import signal
import time

"""
Python プログラムを systemd でサービス化して使うとき stop で停止させるときに便利なもの

## 参考 URL
* DevelopersIO - 【systemd】Pythonでstopを検知する＆例外時に自動で再起動する
https://dev.classmethod.jp/articles/detect-systemd-stop-and-restart-automatically-on-error-with-python/
"""

class TerminatedException(Exception):
    pass

def raise_exception(*_):
    raise TerminatedException()

def set_signal_handling():
    signal.signal(signal.SIGTERM, raise_exception)

if __name__ == "__main__":
    set_signal_handling()

    # (preprocess)    

    # execute
    try:
        # (execute process)
        while True:
            time.sleep(1)

    # (1) if ctrl-C is pushed, stop program nomally
    except KeyboardInterrupt:
        print("KeyboardInterrupt: stopped by keyboard input (ctrl-C)")

    # (2) if stopped by systemd, stop program nomally
    except TerminatedException:
        print("TerminatedExecption: stopped by systemd")

    # (3) if error is caused with network, restart program by systemd
    except OSError as e:
        import traceback
        traceback.print_exc()

        print("NETWORK_ERROR")

        # program will be restarted automatically by systemd (Restart on-failure)
        raise e

    # (4) if other error, restart program by systemd
    except Exception as e:
        import traceback
        traceback.print_exc()

        print("UNKNOWN_ERROR")

        # program will be restarted automatically by systemd (Restart on-failure)
        raise e
