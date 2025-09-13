import os
import time
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD = int(os.getenv("BAUD", "115200"))
MOCK = os.getenv("MOCK_SERIAL", "false").lower() == "true"

class MatrixSerial:
    def __init__(self):
        self.ser = None
        if MOCK:
            print("[MOCK] Serial disabled; logging commands")
        else:
            self._open()

    def _open(self):
        import serial  # pyserial
        print(f"[SERIAL] Opening {PORT} @ {BAUD} 8N1")
        self.ser = serial.Serial(
            PORT,
            BAUD,
            timeout=1.0,                         # longer to allow device to answer
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )
        # Some adapters/devices like a quick DTR/RTS pulse
        try:
            self.ser.setDTR(True); self.ser.setRTS(True)
            time.sleep(0.05)
            self.ser.setDTR(False); self.ser.setRTS(False)
        except Exception:
            pass
        print("[SERIAL] Opened")

    def close(self):
        if self.ser and getattr(self.ser, "is_open", False):
            try:
                self.ser.close()
                print("[SERIAL] Closed")
            except Exception as e:
                print("[SERIAL] Close error:", e)

    def send(self, payload: bytes):
        """
        Send a command (must already include the '!' terminator) and
        read back the device's reply, using an inter-byte idle window.
        """
        if MOCK:
            print("[MOCK SEND]", payload)
            time.sleep(0.05)
            return b"OK"

        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial not open")

        # Clear any stale bytes before we write
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        # Write the command
        self.ser.write(payload)
        self.ser.flush()

        # Read with overall deadline + idle window extension
        chunks = []
        overall_deadline = time.time() + 1.2   # total window to collect a reply
        idle_deadline = time.time() + 0.25     # extend after each new data burst
        last_total = 0

        while time.time() < overall_deadline:
            # Read whatever is buffered (non-blocking)
            n = self.ser.in_waiting
            if n:
                data = self.ser.read(n)
                if data:
                    chunks.append(data)
                    # extend idle window ~250ms after last byte received
                    idle_deadline = time.time() + 0.25

            total = sum(len(c) for c in chunks)
            # If no new data has arrived and the idle window passed, stop
            if total == last_total and time.time() > idle_deadline:
                break
            last_total = total

            time.sleep(0.02)  # small inter-poll gap

        return b"".join(chunks)

    def send_many(self, payloads):
        responses = []
        for p in payloads:
            responses.append(self.send(p))
        return responses
