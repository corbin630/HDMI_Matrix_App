def term(s: str) -> bytes:
    # Matrix expects ASCII ending with '!'
    return f"{s.strip()}!".encode("ascii")

def cmd_single(out_num: int) -> bytes:
    # s output <n> multiview 1!
    return term(f"s output {out_num} multiview 1")

def cmd_audio_follow(out_num: int) -> bytes:
    # 0 = follow selected source/window-1 (per manual)
    return term(f"s output {out_num} audio 0")

def cmd_quad_mode(out_num: int, mode: int = 1) -> bytes:
    # quad screen = 5; then set quad mode 1|2
    # (first put output in quad, then set the layout mode)
    return [term(f"s output {out_num} multiview 5"),
            term(f"s output {out_num} quad mode {mode}")]

def cmd_set_window_input(out_num: int, window: int, src: int) -> bytes:
    return term(f"s output {out_num} window {window} in {src}")

import re

def term(s: str) -> bytes:
    return f"{s.strip()}!".encode("ascii")

# --- queries ---
def q_out_multiview(out_num: int) -> bytes:
    return term(f"r output {out_num} multiview")

def q_out_in_source(out_num: int) -> bytes:
    return term(f"r output {out_num} in source")

def q_window_in_source(out_num: int, window: int) -> bytes:
    return term(f"r output {out_num} window {window} in")

# --- borders ---
def cmd_border(out_num: int, window: int, on: bool) -> bytes:
    return term(f"s output {out_num} window {window} border {1 if on else 0}")

def cmd_border_color(out_num: int, window: int, color_code: int) -> bytes:
    # 2 = RED per manual
    return term(f"s output {out_num} window {window} border color {color_code}")

# --- helpers to parse replies like "output 1 in source: HDMI 2"
RE_HDMI_NUM = re.compile(rb"HDMI\s*(\d)")
RE_MODE = re.compile(rb"(single screen|quad screen|PIP|PBP|triple)")
def parse_hdmi_number(reply: bytes) -> int | None:
    m = RE_HDMI_NUM.search(reply or b"")
    return int(m.group(1)) if m else None

def is_mode(reply: bytes, target: str) -> bool:
    m = RE_MODE.search(reply or b"")
    return (m and m.group(1).decode().lower().startswith(target.lower())) or False

def cmd_route_output_input(out_num: int, src: int) -> bytes:
    # Route HDMI <src> to output <out_num>
    # e.g., s output 1 in source 3!
    return term(f"s output {out_num} in source {src}")

def cmd_prepare_single(out_num: int) -> list[bytes]:
    # Ensure single mode + audio follows the source
    return [
        term(f"s output {out_num} multiview 1"),
        term(f"s output {out_num} audio 0"),
    ]
