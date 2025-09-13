import re

def term(s: str) -> bytes:
    """Matrix expects ASCII ending with '!'."""
    return f"{s.strip()}!".encode("ascii")

# --- core set commands ---
def cmd_single(out_num: int) -> bytes:
    # s output <n> multiview 1!
    return term(f"s output {out_num} multiview 1")

def cmd_audio_follow(out_num: int) -> bytes:
    # 0 = follow selected source/window-1 (per manual)
    return term(f"s output {out_num} audio 0")

def cmd_quad_mode(out_num: int, mode: int = 1) -> list[bytes]:
    """
    Put output in quad multiview, then set the quad layout (1 or 2).
    Returns two commands.
    """
    return [
        term(f"s output {out_num} multiview 5"),
        term(f"s output {out_num} quad mode {mode}")
    ]

def cmd_set_window_input(out_num: int, window: int, src: int) -> bytes:
    return term(f"s output {out_num} window {window} in {src}")

def cmd_route_output_input(out_num: int, src: int) -> bytes:
    # Route HDMI <src> to output <out_num>, e.g., s output 1 in source 3!
    return term(f"s output {out_num} in source {src}")

def cmd_prepare_single(out_num: int) -> list[bytes]:
    # Ensure single mode + audio follows the source
    return [
        term(f"s output {out_num} multiview 1"),
        term(f"s output {out_num} audio 0"),
    ]

# --- queries ---
def q_out_multiview(out_num: int) -> bytes:
    return term(f"r output {out_num} multiview")

def q_out_in_source(out_num: int) -> bytes:
    return term(f"r output {out_num} in source")

def q_window_in_source(out_num: int, window: int) -> bytes:
    return term(f"r output {out_num} window {window} in")

def q_out_quad_mode(out_num: int) -> bytes:
    # Many units reply with both "quad screen" and "quad mode N" here
    return term(f"r output {out_num} quad mode")

# --- borders ---
def cmd_border(out_num: int, window: int, on: bool) -> bytes:
    return term(f"s output {out_num} window {window} border {1 if on else 0}")

def cmd_border_color(out_num: int, window: int, color_code: int) -> bytes:
    # 2 = RED per manual
    return term(f"s output {out_num} window {window} border color {color_code}")

# --- helpers & parsers ---
# Parse replies like "output 1 in source: HDMI 2"
RE_HDMI_NUM = re.compile(rb"HDMI\s*(\d)")

def parse_hdmi_number(reply: bytes) -> int | None:
    m = RE_HDMI_NUM.search(reply or b"")
    return int(m.group(1)) if m else None

# Textual multiview mode words we might see
RE_MODE_TXT = re.compile(rb"(single screen|quad screen|PIP|PBP|triple)", re.I)
# Numeric styles we might see, e.g., "multiview: 5" or bare "5"
RE_MODE_NUM = re.compile(rb"multiview[:\s]*([1-5])", re.I)
RE_BARE_NUM = re.compile(rb"^\s*([1-5])\s*$")

def parse_multiview_mode(reply: bytes) -> int | None:
    """
    Map the device's multiview report to 1..5:
      1=single, 2=PIP, 3=PBP, 4=triple, 5=quad
    Handles both textual and numeric firmware replies.
    """
    if not reply:
        return None
    t = reply.lower()

    # textual mapping
    m = RE_MODE_TXT.search(t)
    if m:
        word = m.group(1)
        if b"single" in word: return 1
        if b"pip"    in word: return 2
        if b"pbp"    in word: return 3
        if b"triple" in word: return 4
        if b"quad"   in word: return 5

    # numeric mapping: "... multiview: N"
    m = RE_MODE_NUM.search(t)
    if m:
        return int(m.group(1))

    # bare number: "1".."5"
    m = RE_BARE_NUM.search(t)
    if m:
        return int(m.group(1))

    return None

def is_mode(reply: bytes, target: str) -> bool:
    """
    Back-compat textual check (kept so existing code doesn't break).
    Prefer parse_multiview_mode() for robust behavior.
    """
    m = RE_MODE_TXT.search(reply or b"")
    return (m and m.group(1).decode().lower().startswith(target.lower())) or False

# Quad-mode specific parsing (e.g., "output 2 quad mode 1")
RE_QUAD_MODE = re.compile(rb"quad mode\s*(\d)", re.I)

def parse_quad_mode_number(reply: bytes) -> int | None:
    if not reply:
        return None
    m = RE_QUAD_MODE.search(reply)
    return int(m.group(1)) if m else None

def is_quad_from_quadmode(reply: bytes) -> bool:
    """
    Treat presence of either 'quad screen' or 'quad mode' in the reply
    as sufficient evidence we're in quad multiview.
    """
    t = (reply or b"").lower()
    return (b"quad screen" in t) or (b"quad mode" in t)
