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