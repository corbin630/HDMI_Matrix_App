from fastapi import APIRouter
from services.state_cache import CACHE
from services.featured import ensure_featured_applied


router = APIRouter()

def _derive_featured(d: dict) -> int:
    """
    If OUT1 is single: featured should be the routed video source (out1_src),
    else (quad): featured should be the current audio source (out1_audio).
    Fall back to existing featured or HDMI 1.
    """
    mode = d.get("out1_mode", "single")
    if mode == "single":
        return d.get("out1_src") or d.get("out1_audio") or (CACHE.featured_source or 1)
    else:  # quad
        return d.get("out1_audio") or (CACHE.featured_source or 1)

@router.get("/api/ui")
def read_ui_state():
    d = CACHE.data or {}

    out1_mode = d.get("out1_mode", "single")
    out1_map  = d.get("out1_map") or {}
    out1_src  = d.get("out1_src")

    out2_mode = d.get("out2_mode")
    out2_map  = d.get("out2_map") or {}
    out2_layout = d.get("out2_quad_layout")

    # Single global color id (default RED=2)
    color_id = d.get("border_color_id", 2)

    # Keep featured consistent with current mode/routing
    mode = out1_mode
    if mode == "single":
        featured = d.get("out1_src") or d.get("out1_audio") or (CACHE.featured_source or 1)
    else:
        featured = d.get("out1_audio") or (CACHE.featured_source or 1)
    if featured != (CACHE.featured_source or None):
        CACHE.featured_source = featured

    return {
        "out1_mode": out1_mode,
        "out1_map": out1_map,
        "out1_src": out1_src,
        "featured_source": featured,
        "border_color_id": color_id,
        "out2_mode": out2_mode,
        "out2_map": out2_map,
        "out2_quad_layout": out2_layout,
    }

@router.post("/api/reconcile-ui")
def reconcile_ui():
    d = CACHE.data or {}
    featured = _derive_featured(d)
    CACHE.featured_source = featured
    ensure_featured_applied()   # keeps your preferred ordering inside your service
    # return current UI state after reconciliation
    return read_ui_state()

@router.post("/api/init/full")
def init_full():
    COLOR_ID_RED = 2  # single global palette id

    # 1) Store one global color id
    d = CACHE.data or {}
    d["border_color_id"] = COLOR_ID_RED
    CACHE.data = d

    # 2) Prime that color on both outputs (pre-write color, borders hidden)
    try:
        borders.prime_color_all(1, COLOR_ID_RED)
        borders.prime_color_all(2, COLOR_ID_RED)
    except TypeError:
        borders.prime_color_all(1)
        borders.prime_color_all(2)

    # 3) Choose featured and set outputs (video/audio first, per your preference)
    mode = d.get("out1_mode", "single")
    if mode == "single":
        featured = d.get("out1_src") or d.get("out1_audio") or (CACHE.featured_source or 1)
    else:
        featured = d.get("out1_audio") or (CACHE.featured_source or 1)
    CACHE.featured_source = featured

    set_single(1, featured)   # video
    set_follow(1)             # audio
    set_quad_14(2)            # OUT2 quad 1..4

    # 4) Apply featured (borders/highlights)
    ensure_featured_applied()

    # 5) Return updated snapshot
    return read_ui_state()

