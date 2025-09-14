# routes/misc.py
from fastapi import APIRouter, HTTPException, Path as FPath
import vendor.commands as C
from services.serial_io import SER
from services.state_cache import CACHE
from services.borders import clear_all, set_highlight, set_border_color, prime_color_all
from services.video import set_single, set_quad_14, ensure_map_cached
from services.startup import cold_boot_init  # uses your priming routine

router = APIRouter(prefix="/api")

@router.post("/one-single-two-quad14")
def one_single_two_quad14():
    """
    OUT1: single + audio follow + clear borders
    OUT2: quad mode 1 with inputs 1..4 mapped to windows 1..4
    """
    try:
        # OUT1 single + follow + clear borders
        set_single(1)                   # put OUT1 in single (no specific src)
        SER.send_set(C.cmd_audio_follow(1), delay=0.003)
        clear_all(1)
        CACHE.set("out1_audio", 0)      # 0 = follow

        # OUT2 quad with 1..4
        set_quad_14(2)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-borders/{out_num}")
def clear_borders_route(out_num: int = FPath(..., ge=1, le=2)):
    try:
        clear_all(out_num)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "out": out_num, "cleared_windows": [1, 2, 3, 4]}

@router.post("/clear-borders-both")
def clear_borders_both():
    try:
        clear_all(1)
        clear_all(2)
        return {"status": "ok", "cleared": {"out1": [1,2,3,4], "out2": [1,2,3,4]}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/outline-current-on-quad")
def outline_current_on_quad():
    """
    Outline the current 'featured' source on OUT2 (when OUT2 is in quad).
    If no featured is set yet, fall back to OUT1 single source if available.
    """
    try:
        if CACHE.get("out2_mode") != "quad":
            return {"status": "noop", "reason": "out2_not_quad"}

        src = CACHE.featured_source or CACHE.get("out1_src") or 1
        mp = ensure_map_cached(2)
        win = next((w for w, s in mp.items() if s == src), None)
        if win:
            # Use new faster API: only toggle what changed
            set_highlight(2, win, color=2)
            CACHE.set("out2_border_window", win)
            return {"status": "ok", "out2_window": win, "src": src}
        return {"status": "noop", "reason": "src_not_in_out2_map", "src": src}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ping")
def ping():
    return {"reply": SER.send(b"r output 1 multiview!").decode(errors="ignore")}

@router.get("/test-modes")
def test_modes():
    raw_mv = SER.send(C.q_out_multiview(2))
    raw_qm = SER.send(C.term("r output 2 quad mode"))
    return {"multiview_raw": repr(raw_mv), "quadmode_raw": repr(raw_qm)}

# --------- Manual priming endpoint ---------
@router.post("/init")
def manual_init():
    """
    Manually prime the matrix:
      - OUT1 single + audio follow
      - OUT2 quad (1..4 mapped)
      - Cache window maps for OUT1/OUT2
      - Prime border color to all windows (and hide borders)
    Safe to re-run (e.g., after power-cycling the matrix).
    """
    try:
        cold_boot_init()
        return {"status": "ok", "primed": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------- Optional: set border color via API (future UI) ---------
@router.post("/border-color/{out_num}/{color}")
def set_border_color_route(out_num: int = FPath(..., ge=1, le=2), color: int = FPath(..., ge=1, le=7)):
    """
    Set the 'armed' border color for an output and prime it on all windows.
    If a window is currently highlighted, recolor just that window.
    """
    try:
        set_border_color(out_num, color)
        prime_color_all(out_num, color)
        return {"status": "ok", "out": out_num, "color": color}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
