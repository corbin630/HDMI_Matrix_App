import os
import time
import threading
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD = int(os.getenv("BAUD", "115200"))
MOCK = os.getenv("MOCK_SERIAL", "false").lower() == "true"
AUTO_BAUD = os.getenv("AUTO_BAUD", "true").lower() == "true"

# benign probe used for warm-up & autosync
TEST_QUERY = b"r power!"


class MatrixSerial:
    def __init__(self):
        self.ser = None
        self._lock = threading.Lock()
        self._status_cache = None
        self._status_ts = 0.0

        if MOCK:
            print("[MOCK] Serial disabled; logging commands")
            return

        # Open with a warm-up sequence that mirrors your manual flip.
        ok = self._open_warm()
        if not ok:
            print("[SERIAL] ⚠️ Warm-up finished but could not confirm reply; continuing anyway")

        # Optional autosync pass (robust, but non-fatal if it fails)
        if AUTO_BAUD:
            try:
                if self._autosync():
                    print("[SERIAL] Autosync OK")
                else:
                    print("[SERIAL] ⚠️ Autosync did not get a reply")
            except Exception as e:
                print(f"[SERIAL] ⚠️ Autosync error: {e}")

    # ---------------- low-level open/close ----------------

    def _base_open(self, baud: int):
        import serial
        print(f"[SERIAL] Opening {PORT} @ {baud} 8N1")
        self.ser = serial.Serial(
            PORT,
            baud,
            timeout=1.0,
            write_timeout=1.0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )
        self._pulse_lines(0.03)
        print("[SERIAL] Opened")

    def _open_warm(self) -> bool:
        """
        1) Try target BAUD.
        2) If that fails, open @9600, send a quick probe, then switch the SAME handle
           to target BAUD and probe again. Never raise; always return True/False.
        """
        import serial
        try:
            self._base_open(BAUD)
            # quick non-fatal probe
            _ = self._quick_probe(wait=0.20)
            return True
        except serial.SerialException as e:
            print("[SERIAL] Target-baud open failed; trying warm-up @ 9600 …")

        # Try 9600 open
        try:
            self._base_open(9600)
        except Exception as e2:
            time.sleep(0.2)
            try:
                self._base_open(9600)
            except Exception as e3:
                print(f"[SERIAL] ❌ Could not open @9600 either: {e3}")
                return False

        # At 9600: nudge, then flip baudrate on the same handle
        got_reply_9600 = False
        try:
            _ = self._quick_probe(wait=0.25)
            got_reply_9600 = True
        except Exception as e:
            print(f"[SERIAL] (warn) 9600 quick probe error: {e}")

        try:
            with self._lock:
                self.ser.baudrate = BAUD
            time.sleep(0.15)
            self._pulse_lines(0.03)
        except Exception as e:
            print(f"[SERIAL] (warn) baudrate flip error: {e}")

        # Confirm at target baud (non-fatal)
        try:
            _ = self._quick_probe(wait=0.25)
            print(f"[SERIAL] Warm-up flip to {BAUD} complete (9600 reply={got_reply_9600})")
            return True
        except Exception as e:
            print(f"[SERIAL] (warn) no reply after flip to {BAUD}: {e}")
            return False

    def _reopen(self, baud: int):
        if self.ser and getattr(self.ser, "is_open", False):
            try:
                self.ser.close()
            except Exception:
                pass
        self._base_open(baud)

    def _pulse_lines(self, delay: float = 0.03):
        try:
            self.ser.setDTR(True);  self.ser.setRTS(True)
            time.sleep(delay)
            self.ser.setDTR(False); self.ser.setRTS(False)
        except Exception:
            pass

    def close(self):
        if self.ser and getattr(self.ser, "is_open", False):
            try:
                self.ser.close()
                print("[SERIAL] Closed")
            except Exception as e:
                print("[SERIAL] Close error:", e)

    # ---------------- helpers / probes ----------------

    def _term(self, s: str) -> bytes:
        return (s.strip() + "!").encode("ascii")

    def _quick_probe(self, wait: float = 0.15) -> bytes:
        """Short write/read used only during open/warmup. Raises on port problems."""
        with self._lock:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self.ser.write(TEST_QUERY)
            self.ser.flush()
            time.sleep(wait)
            return self.ser.read_all()

    def _query_power(self) -> bytes:
        """Robust power read using the full send/read loop."""
        return self.send(self._term("r power"))

    # ---------------- autosync (non-fatal) ----------------

    def _autosync(self) -> bool:
        rep = self._query_power()
        if rep:
            return True

        print("[SERIAL] No reply; trying 9600 sync hop…")
        self._reopen(9600)
        rep = self._query_power()
        if rep:
            print("[SERIAL] 9600 replied; switching back to high baud")
            self._reopen(BAUD)
            rep2 = self._query_power()
            return bool(rep2)

        print("[SERIAL] Final attempt with DTR/RTS pulse at configured baud…")
        self._reopen(BAUD)
        self._pulse_lines(0.05)
        rep3 = self._query_power()
        return bool(rep3)

    # ---------------- status snapshot (cached) ----------------

    def status_snapshot(self, min_interval: float = 0.8) -> dict:
        now = time.time()
        connected = bool(self.ser and getattr(self.ser, "is_open", False))
        if not connected:
            snap = {"connected": False, "responsive": False, "power": "unknown"}
            self._status_cache = snap
            self._status_ts = now
            return snap

        if (now - self._status_ts) < min_interval and self._status_cache:
            return self._status_cache

        rep = self._query_power()
        txt = (rep or b"").strip().lower()
        responsive = bool(rep)
        power = "unknown"
        if b"on" in txt:
            power = "on"
        elif b"off" in txt:
            power = "off"

        snap = {"connected": True, "responsive": responsive, "power": power}
        self._status_cache = snap
        self._status_ts = now
        return snap

    # ---------------- send APIs ----------------

    def send(self, payload: bytes):
        """
        Use for queries where you expect a reply.
        Robust read loop with inter-byte idle window.
        """
        if MOCK:
            print("[MOCK SEND]", payload)
            time.sleep(0.05)
            return b"OK"

        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial not open")

        with self._lock:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass

            self.ser.write(payload)
            self.ser.flush()

            chunks = []
            overall_deadline = time.time() + 1.2
            idle_deadline = time.time() + 0.25
            last_total = 0

            while time.time() < overall_deadline:
                n = self.ser.in_waiting
                if n:
                    data = self.ser.read(n)
                    if data:
                        chunks.append(data)
                        idle_deadline = time.time() + 0.25

                total = sum(len(c) for c in chunks)
                if total == last_total and time.time() > idle_deadline:
                    break
                last_total = total
                time.sleep(0.02)

            return b"".join(chunks)

    def send_set(self, payload: bytes, delay: float = 0.01):
        """
        Fast path for 'set' commands (no readback). Keeps UI snappy.
        """
        if MOCK:
            print("[MOCK SEND-SET]", payload)
            time.sleep(delay)
            return b"OK"

        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial not open")

        with self._lock:
            self.ser.write(payload)
            self.ser.flush()
        time.sleep(delay)
        return b""

    def send_many(self, payloads):
        return [self.send(p) for p in payloads]

    def send_many_set(self, payloads, delay_each: float = 0.01):
        for p in payloads:
            self.send_set(p, delay_each)
        return b""
