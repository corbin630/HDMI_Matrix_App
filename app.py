from fastapi import FastAPI, HTTPException, Path as FPath
from fastapi.responses import FileResponse
from serial_driver import MatrixSerial
import commands as C
from pathlib import Path
from time import time, sleep

app = FastAPI(title="HDMI Matrix Controller")
SER = MatrixSerial()

# ---------------- In-memory state cache ----------------
class MatrixCache:
    """
    Keep track of what OUR app has set so we can avoid re-querying the device
    on every click. We still offer a 'Refresh State' endpoint to re-learn
    when the device was changed out-of-band.
    """
    def __init__(self):
        self.data = {}
        self.ts = {}
    def set(self, k, v):
        self.data[k] = v; self.ts[k] = time()
    def get(self, k, max_age=None):
        if k not in self.data:
            return None
        if max_age is not None and (time() - self.ts.get(k, 0)) > max_age:
            return None
        return self.data[k]
    def clear(self, prefix=None):
        if prefix is None:
            self.data.clear(); self.ts.clear()
        else:
            for k in list(self.data.keys()):
                if str(k).startswith(prefix):
                    self.data.pop(k, None); self.ts.pop(k, None)

CACHE = MatrixCache()

# ---------------- Helpers ----------------
def _ensure_out2_map_cached():
    """Discover OUT2 window->HDMI map only if cache is empty."""
    out2_map = CACHE.get("out2_map")
    if out2_map:
        return out2_map
    # One-time discovery
    m = {}
    for w in range(1, 5):
        rep = SER.send(C.q_window_in_source(2, w))
        m[w] = C.parse_hdmi_number(rep)
        sleep(0.02)
    CACHE.set("out2_map", m)
    return m

# ---------------- Routes ----------------
@app.get("/")
def root():
    return FileResponse(Path("static/index.html"))

@app.get("/api/status")
def status():
    if SER is None:
        return {"connected": False, "responsive": False, "power": "unknown"}
    return SER.status_snapshot()

@app.post("/api/refresh-state")
def refresh_state():
    """
    Re-learn device state with a few queries and repopulate the cache.
    Useful after power cycles or when state changed outside this app.
    """
    try:
        # OUT1 mode
        mv1 = SER.send(C.q_out_multiview(1))
        m1 = C.parse_multiview_mode(mv1)
        CACHE.set("out1_mode", "single" if m1 == 1 else "other")

        # OUT1 current source (HDMI n)
        rep = SER.send(C.q_out_in_source(1))
        hdmi = C.parse_hdmi_number(rep)
        if hdmi:
            CACHE.set("out1_src", hdmi)

        # OUT2 quad?
        qm2 = SER.send(C.q_out_quad_mode(2))
        if C.is_quad_from_quadmode(qm2):
            CACHE.set("out2_mode", "quad")
            qnum = C.parse_quad_mode_number(qm2) or 1
            CACHE.set("out2_quad_layout", qnum)
            # Refresh window->HDMI map
            _ensure_out2_map_cached()
        else:
            CACHE.set("out2_mode", "other")

        return {"status": "ok", "cache": CACHE.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/one-single-two-quad14")
def one_single_two_quad14():
    """
    Output 1: single + audio follow
    Output 2: quad mode 1 with inputs 1,2,3,4 in windows 1..4
    """
    try:
        # OUT1 single & audio follow (fast setters; no replies)
        SER.send_many_set([
            C.cmd_single(1),
            C.cmd_audio_follow(1),
        ], delay_each=0.003)
        CACHE.set("out1_mode", "single")

        # OUT2 quad mode 1
        SER.send_many_set(C.cmd_quad_mode(2, mode=1), delay_each=0.003)
        CACHE.set("out2_mode", "quad")
        CACHE.set("out2_quad_layout", 1)

        # Map windows: 1->1, 2->2, 3->3, 4->4
        SER.send_many_set([
            C.cmd_set_window_input(2, 1, 1),
            C.cmd_set_window_input(2, 2, 2),
            C.cmd_set_window_input(2, 3, 3),
            C.cmd_set_window_input(2, 4, 4),
        ], delay_each=0.003)
        CACHE.set("out2_map", {1:1, 2:2, 3:3, 4:4})

        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/out1/select/{src}")
def out1_select(src: int = FPath(..., ge=1, le=4)):
    """
    Set Output 1 to single mode (audio follow) and route HDMI {src} to Output 1.
    Uses fast setters and caches state for instant subsequent actions.
    """
    try:
        SER.send_many_set([
            C.cmd_single(1),
            C.cmd_audio_follow(1),
            C.cmd_route_output_input(1, src),
        ], delay_each=0.003)
        CACHE.set("out1_mode", "single")
        CACHE.set("out1_src", src)
        return {"status": "ok", "out": 1, "src": src}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear-borders/{out_num}")
def clear_borders(out_num: int = FPath(..., ge=1, le=2)):
    """
    Turn OFF all window borders on the given output (1 or 2) quickly (no queries).
    """
    try:
        SER.send_many_set([C.cmd_border(out_num, w, False) for w in range(1, 5)], delay_each=0.003)
        return {"status": "ok", "out": out_num, "cleared_windows": [1, 2, 3, 4]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outline-current-on-quad")
def outline_current_on_quad():
    """
    If OUT1 is single and OUT2 is quad:
      - determine OUT1 source (prefer cache)
      - determine OUT2 window showing that source (prefer cache)
      - clear borders then outline that window in RED, fast
    Otherwise: do nothing (no error).
    """
    try:
        # Prefer cached modes
        out1_mode = CACHE.get("out1_mode")
        out2_mode = CACHE.get("out2_mode")

        # Fallback checks if cache is cold
        if out1_mode != "single":
            mv1 = SER.send(C.q_out_multiview(1))
            if C.parse_multiview_mode(mv1) == 1:
                CACHE.set("out1_mode", "single")
            else:
                return {"status": "skipped", "reason": "OUT1 not single"}

        if out2_mode != "quad":
            qm2 = SER.send(C.q_out_quad_mode(2))
            if C.is_quad_from_quadmode(qm2):
                CACHE.set("out2_mode", "quad")
            else:
                return {"status": "skipped", "reason": "OUT2 not quad"}

        # OUT1 current HDMI
        hdmi_n = CACHE.get("out1_src")
        if not hdmi_n:
            src1 = SER.send(C.q_out_in_source(1))
            hdmi_n = C.parse_hdmi_number(src1)
            if not hdmi_n:
                return {"status": "skipped", "reason": f"cannot parse OUT1 source"}
            CACHE.set("out1_src", hdmi_n)

        # OUT2 window map
        out2_map = CACHE.get("out2_map")
        if not out2_map:
            out2_map = _ensure_out2_map_cached()

        # Find which window shows OUT1's source
        target_window = next((w for w, h in out2_map.items() if h == hdmi_n), None)
        if not target_window:
            return {"status": "skipped", "reason": "no OUT2 window matched"}

        # Fast border ops with enforced RED (2) to prevent default yellow flash
        SER.send_many_set([C.cmd_border(2, w, False) for w in range(1, 5)], delay_each=0.003)
        SER.send_many_set([
            C.cmd_border_color(2, target_window, 2),  # set RED first
            C.cmd_border(2, target_window, True),     # enable border
            C.cmd_border_color(2, target_window, 2),  # re-assert RED (some FW latches here)
        ], delay_each=0.003)

        CACHE.set("out2_border_window", target_window)
        return {"status": "ok", "outlined_window": target_window, "hdmi": hdmi_n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Existing test/debug routes (left intact) ---
@app.get("/api/ping")
def ping():
    return {"reply": SER.send(b"r output 1 multiview!").decode(errors="ignore")}

@app.get("/api/test-modes")
def test_modes():
    raw_mv = SER.send(C.q_out_multiview(2))
    raw_qm = SER.send(C.term("r output 2 quad mode"))
    return {
        "multiview_raw": repr(raw_mv),
        "quadmode_raw": repr(raw_qm),
    }
