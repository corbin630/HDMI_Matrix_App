# services/featured.py
from services.state_cache import CACHE
from services.audio import set_audio_hdmi, set_follow
from services.borders import clear_all, set_highlight
from services.video import set_single, ensure_map_cached, set_quad_14

BATCH_DELAY = 0.001  # 1 ms: faster but safe for typical USB-serial

def _win_for_src(out_n: int, src: int):
    mp = ensure_map_cached(out_n)
    for w, s in mp.items():
        if s == src:
            return w
    return None

def _mirror_on_out2(src: int):
    """
    Try to outline the same source on OUT2 (quad expected, but we don't hard-require the cached flag).
    If the source isn't present in OUT2's current map, do nothing.
    """
    win2 = _win_for_src(2, src)
    if win2:
        set_highlight(2, win2, color=2, delay_each=BATCH_DELAY)
        CACHE.set("out2_border_window", win2)

def ensure_featured_applied():
    """
    Apply Featured Source with audio-first, then borders.
    SINGLE: route OUT1 to featured + audio follow; clear OUT1 border; mirror border on OUT2 if its map has the source.
    QUAD:   audio to featured; outline on OUT1; mirror outline on OUT2.
    """
    fs = CACHE.featured_source
    if fs is None:
        return

    mode = CACHE.get("out1_mode")
    if mode is None:
        # Be defensive: try a best-effort inference from prior actions; default to single
        mode = "single"
        CACHE.set("out1_mode", mode)

    if mode == "single":
        # 1) Audio first
        set_audio_hdmi(1, fs)

        # 2) Video route + follow
        set_single(1, fs)     # sets mode=single, routes video
        set_follow(1)         # sets audio follow 0
        CACHE.set("out1_src", fs)

        # 3) Borders: clear OUT1, mirror highlight on OUT2
        clear_all(1, delay_each=BATCH_DELAY)
        _mirror_on_out2(fs)

    else:  # "quad" (or anything not "single")
        # 1) Audio first
        set_audio_hdmi(1, fs)

        # 2) Highlight on OUT1
        win1 = _win_for_src(1, fs)
        if win1:
            set_highlight(1, win1, color=2, delay_each=BATCH_DELAY)
            CACHE.set("out1_border_window", win1)

        # 3) Mirror on OUT2
        _mirror_on_out2(fs)
