from time import time
from serial_driver import MatrixSerial
from services.state_cache import CACHE
SER = MatrixSerial()

def send_if_changed(key: str, cmd: bytes | str, min_gap=0.12):
    now = time(); last = CACHE.ts.get(f"last:{key}", 0.0)
    if (now-last) < min_gap: return
    SER.send(cmd if isinstance(cmd,(bytes,bytearray)) else cmd.encode())
    CACHE.ts[f"last:{key}"] = now
