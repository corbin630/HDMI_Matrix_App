import vendor.commands as C
from services.serial_io import send_if_changed
from services.state_cache import CACHE
def set_audio_hdmi(out_n: int, src: int):
    send_if_changed(f"o{out_n}_audio", C.term(f"s output {out_n} audio {src}"))
    CACHE.set(f"out{out_n}_audio", src)
def set_follow(out_n: int):
    send_if_changed(f"o{out_n}_audio_follow", C.cmd_audio_follow(out_n))
    CACHE.set(f"out{out_n}_audio", 0)
