import os
import time
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD = int(os.getenv("BAUD", "115200"))
MOCK = os.getenv("MOCK_SERIAL", "false").lower() == "true"

class MatrixSerial:
    def __init__(self):
        if MOCK:
            self.ser = None
            print("[MOCK] Serial disabled; logging commands")
        else:
            import serial  # pyserial
            self.ser = serial.Serial(PORT, BAUD, timeout=0.3, bytesize=8, parity='N', stopbits=1)

    def send(self, payload: bytes):
        if MOCK:
            print("[MOCK SEND]", payload)
            time.sleep(0.05)
            return b"OK"
        self.ser.write(payload)
        self.ser.flush()
        # If your device returns a reply, read it (optional)
        time.sleep(0.05)
        return self.ser.read_all()

    def send_many(self, payloads):
        responses = []
        for p in payloads:
            responses.append(self.send(p))
        return responses