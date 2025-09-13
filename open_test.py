# open_test.py
import serial, time

PORT = "COM3"        # <-- if your adapter shows another COM, change this
BAUD = 115200

print(f"Opening {PORT} @ {BAUD} 8N1 ...")
ser = serial.Serial(
    PORT, BAUD, timeout=0.3,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    rtscts=False, dsrdtr=False, xonxoff=False
)
time.sleep(0.2)
print("Opened?", ser.is_open)
ser.close()
print("Closed.")
