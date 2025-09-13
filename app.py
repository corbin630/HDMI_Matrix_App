from fastapi import FastAPI, HTTPException, Path as FPath
from fastapi.responses import FileResponse
from serial_driver import MatrixSerial
import commands as C
from pathlib import Path
import time

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
    
@app.post("/api/outline-current-on-quad")
def outline_current_on_quad():
    """
    If OUT1 is single and OUT2 is quad:
      - find the HDMI input on OUT1
      - find the window on OUT2 showing that input
      - turn all OUT2 borders off, then outline that window RED
    Otherwise: do nothing (no error).
    """
    try:
        # 1) modes
        mv1 = SER.send(C.q_out_multiview(1))
        mv2 = SER.send(C.q_out_multiview(2))
        if not (C.is_mode(mv1, "single") and C.is_mode(mv2, "quad")):
            return {"status": "skipped", "reason": "modes not single/quad"}

        # 2) which HDMI on OUT1 single?
        src1 = SER.send(C.q_out_in_source(1))
        hdmi_n = C.parse_hdmi_number(src1)
        if not hdmi_n:
            raise RuntimeError(f"Could not parse OUT1 source from: {src1}")

        # 3) which OUT2 window shows that HDMI?
        target_window = None
        for w in range(1, 5):
            rep = SER.send(C.q_window_in_source(2, w))
            if C.parse_hdmi_number(rep) == hdmi_n:
                target_window = w
                break
            time.sleep(0.02)
        if not target_window:
            return {"status": "skipped", "reason": "no OUT2 window matched"}

        # 4) clear borders, then set red on target
        for w in range(1, 5):
            SER.send(C.cmd_border(2, w, False))
        SER.send(C.cmd_border_color(2, target_window, 2))  # 2 = RED
        SER.send(C.cmd_border(2, target_window, True))

        return {"status": "ok", "outlined_window": target_window, "hdmi": hdmi_n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/out1/select/{src}")
def out1_select(src: int = FPath(..., ge=1, le=4)):
    """
    Set Output 1 to single mode (audio follow) and route HDMI {src} to Output 1.
    """
    try:
        # Make sure OUT1 is single + audio follow
        for p in C.cmd_prepare_single(1):
            SER.send(p)
        # Route the requested input to OUT1
        SER.send(C.cmd_route_output_input(1, src))
        return {"status": "ok", "out": 1, "src": src}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/clear-borders/{out_num}")
def clear_borders(out_num: int = FPath(..., ge=1, le=2)):
    """
    Turn OFF all window borders on the given output (1 or 2).
    """
    try:
        for w in range(1, 5):
            SER.send(C.cmd_border(out_num, w, False))
        return {"status": "ok", "out": out_num, "cleared_windows": [1, 2, 3, 4]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    