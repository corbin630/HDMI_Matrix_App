from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from serial_driver import MatrixSerial
import commands as C
from pathlib import Path

app = FastAPI(title="HDMI Matrix Controller")
SER = MatrixSerial()

@app.get("/")
def root():
    return FileResponse(Path("static/index.html"))

@app.post("/api/one-single-two-quad14")
def one_single_two_quad14():
    """
    Output 1: single + audio follow
    Output 2: quad mode 1 with inputs 1,2,3,4 in windows 1..4
    """
    try:
        # OUT1 single & audio follow
        SER.send(C.cmd_single(1))
        SER.send(C.cmd_audio_follow(1))

        # OUT2 quad mode 1
        for p in C.cmd_quad_mode(2, mode=1):
            SER.send(p)

        # Map windows: 1->1, 2->2, 3->3, 4->4
        SER.send_many([
            C.cmd_set_window_input(2, 1, 1),
            C.cmd_set_window_input(2, 2, 2),
            C.cmd_set_window_input(2, 3, 3),
            C.cmd_set_window_input(2, 4, 4),
        ])
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))