from fastapi import APIRouter, HTTPException, Path as FPath
import vendor.commands as C
from services.state_cache import CACHE
from services.featured import ensure_featured_applied
from services.video import set_quad_14
from services.serial_io import SER

router = APIRouter(prefix="/api/out1")

@router.post("/quad14")
def out1_quad14():
    """
    OUT1 -> Quad mode 1 (1→1..4). If coming from SINGLE, keep listening to the same HDMI,
    and mark that window with a RED border (audio first, borders next).
    """
    try:
        remembered_hdmi = CACHE.get("out1_src")

        # Switch hardware to quad and map 1..4
        set_quad_14(1)

        # If we have a remembered single source, carry that over as featured
        if remembered_hdmi in (1, 2, 3, 4):
            CACHE.featured_source = remembered_hdmi

        # Apply audio-first, then borders
        ensure_featured_applied()
        return {"status": "ok", "remembered_hdmi": remembered_hdmi, "featured": CACHE.featured_source}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/select/{src}")
def out1_select(src: int = FPath(..., ge=1, le=4)):
    """
    Set Featured Source to {src} and apply it.
    SINGLE: route OUT1 to src + audio follow + clear borders.
    QUAD:   set audio to src; outline the window with src on OUT1 (+ mirror to OUT2 if quad).
    """
    try:
        CACHE.featured_source = src
        ensure_featured_applied()
        mode = CACHE.get("out1_mode")
        return {"status": "ok", "featured": src, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/single-from-current-audio")
def out1_single_from_current_audio():
    """
    Switch OUT1 to single using the last audio source we selected while in quad.
    Clears OUT1 borders. If cache missing, fall back to HDMI 1.
    """
    try:
        audio_hdmi = CACHE.get("out1_audio") or 1
        # Set intent and re-use your orchestrator (audio-first)
        CACHE.featured_source = audio_hdmi
        CACHE.set("out1_mode", "single")
        ensure_featured_applied()
        return {"status": "ok", "out": 1, "src": audio_hdmi}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional: explicit mode endpoints if you want to call them (not used by index.html)
@router.post("/mode/single")
def set_mode_single():
    CACHE.set("out1_mode", "single")
    ensure_featured_applied()
    return {"status": "ok", "out1_mode": "single"}

@router.post("/mode/quad")
def set_mode_quad():
    try:
        return out1_quad14()  # hardware switch + apply featured
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
