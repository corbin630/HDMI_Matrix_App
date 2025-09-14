from services.state_cache import CACHE
from services.video import set_single, set_quad_14, ensure_map_cached
from services.audio import set_follow
from services.borders import prime_color_all, clear_all, set_border_color

DEFAULT_COLOR = 2  # red, matches borders.DEFAULT_COLOR

def cold_boot_init():
    """
    Set a known-good baseline and prime caches & border colors.
    Safe to call on FastAPI startup or via a manual endpoint.
    """
    # 1) Opinionated baseline (optional - comment out if you prefer non-intrusive boot)
    set_single(1)           # OUT1 in single (no specific src)
    set_follow(1)           # OUT1 audio follow
    set_quad_14(2)          # OUT2 quad mode with 1..4 mapping

    # 2) Ensure window maps in cache (faster later decisions)
    ensure_map_cached(1)
    ensure_map_cached(2)

    # 3) Arm default border color per output and prime all windows once
    set_border_color(1, DEFAULT_COLOR)
    set_border_color(2, DEFAULT_COLOR)
    prime_color_all(1, DEFAULT_COLOR)
    prime_color_all(2, DEFAULT_COLOR)

    # 4) Hide borders (we just want color pre-set)
    clear_all(1)
    clear_all(2)

    # 5) Optional: remember default color globally if you track settings
    CACHE.set("border_color_default", DEFAULT_COLOR)
