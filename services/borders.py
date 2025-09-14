import vendor.commands as C
from services.serial_io import SER
from services.state_cache import CACHE

# Default border color (device-dependent; 2 = RED on most OREI units)
DEFAULT_COLOR = 2

def _get_out_state(out_n: int):
    """
    Retrieve per-output border state dict: {"window": Optional[int], "color": int}
    """
    return CACHE.border_state.setdefault(out_n, {"window": None, "color": DEFAULT_COLOR})

def set_border_color(out_n: int, color: int):
    """
    Arm a border color for an output. If a window is currently highlighted,
    recolor just that window (no toggle).
    """
    st = _get_out_state(out_n)
    color = int(color)
    if color == st["color"]:
        return
    st["color"] = color
    cur = st["window"]
    if cur in (1, 2, 3, 4):
        SER.send_many_set([C.cmd_border_color(out_n, cur, color)], delay_each=0.001)

def prime_color_all(out_n: int, color: int | None = None):
    """
    Pre-set the border color on ALL windows, then turn borders off.
    Useful after a power cycle so later highlights don't need extra color writes.
    """
    st = _get_out_state(out_n)
    armed = int(color if color is not None else st["color"])
    batch = []
    # Set color on each window once
    for w in range(1, 5):
        batch.append(C.cmd_border_color(out_n, w, armed))
    # Then ensure all borders are off (hidden)
    for w in range(1, 5):
        batch.append(C.cmd_border(out_n, w, False))
    SER.send_many_set(batch, delay_each=0.001)
    st["window"] = None
    st["color"] = armed

def set_highlight(out_n: int, new_win: int, color: int | None = None, delay_each: float = 0.001):
    """
    Make 'new_win' the only window with a border on output 'out_n'.
    Minimal writes: disable previous (if any) -> set color (if needed) -> enable new.
    Idempotent if the requested window is already highlighted.
    """
    if new_win not in (1, 2, 3, 4):
        return

    st = _get_out_state(out_n)
    target_color = int(st["color"] if color is None else color)
    cur_win = st["window"]

    if cur_win == new_win:
        # Ensure it's on and (re)apply color just in case the matrix cleared it
        SER.send_many_set([
            C.cmd_border_color(out_n, new_win, target_color),
            C.cmd_border(out_n, new_win, True),
        ], delay_each=delay_each)
        return

    batch = []
    if cur_win in (1, 2, 3, 4):
        batch.append(C.cmd_border(out_n, cur_win, False))
    batch.append(C.cmd_border_color(out_n, new_win, target_color))
    batch.append(C.cmd_border(out_n, new_win, True))

    SER.send_many_set(batch, delay_each=delay_each)
    st["window"] = new_win
    st["color"]  = target_color

def clear_all(out_n: int, delay_each: float = 0.001):
    """Turn off all window borders for output 'out_n'."""
    SER.send_many_set([C.cmd_border(out_n, w, False) for w in range(1, 5)], delay_each=delay_each)
    _get_out_state(out_n)["window"] = None
