from fastapi import APIRouter, HTTPException
import vendor.commands as C
from services.serial_io import SER
from services.state_cache import CACHE
from services.video import ensure_map_cached

router = APIRouter(prefix="/api")

@router.get("/status")
def status():
    if SER is None:
        return {"connected": False, "responsive": False, "power": "unknown"}
    return SER.status_snapshot()

@router.post("/refresh-state")
def refresh_state():
    """
    Refresh a few bits of state we care about: OUT1 mode, OUT1 single source,
    and OUT2 mode. Populate window maps on demand (quad only).
    """
    try:
        # OUT1 mode
        mv1 = SER.send(C.q_out_multiview(1))
        m1 = C.parse_multiview_mode(mv1)
        CACHE.set("out1_mode", "single" if m1 == 1 else ("quad" if m1 == 5 else "other"))

        # If quad, cache quad layout + map
        if CACHE.get("out1_mode") == "quad":
            qm1 = SER.send(C.q_out_quad_mode(1))
            qnum1 = C.parse_quad_mode_number(qm1) or 1
            CACHE.set("out1_quad_layout", qnum1)
            ensure_map_cached(1)

        # OUT1 current source (for single mode)
        rep = SER.send(C.q_out_in_source(1))
        hdmi = C.parse_hdmi_number(rep)
        if hdmi:
            CACHE.set("out1_src", hdmi)

        # OUT2 mode
        qm2 = SER.send(C.q_out_quad_mode(2))
        if C.is_quad_from_quadmode(qm2):
            CACHE.set("out2_mode", "quad")
            qnum2 = C.parse_quad_mode_number(qm2) or 1
            CACHE.set("out2_quad_layout", qnum2)
            ensure_map_cached(2)
        else:
            CACHE.set("out2_mode", "other")

        return {"status": "ok", "cache": CACHE.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
