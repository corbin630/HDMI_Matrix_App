import vendor.commands as C
from time import sleep
from services.serial_io import SER
from services.state_cache import CACHE

def set_single(out_n: int, src: int | None = None):
    burst = [C.cmd_single(out_n)]
    if src: burst.append(C.cmd_route_output_input(out_n, src))
    SER.send_many_set(burst, delay_each=0.003)
    CACHE.set(f"out{out_n}_mode","single")
    if src: CACHE.set(f"out{out_n}_src", src)

def set_quad_14(out_n: int):
    SER.send_many_set(C.cmd_quad_mode(out_n, mode=1), delay_each=0.003)
    SER.send_many_set([C.cmd_set_window_input(out_n,i,i) for i in range(1,5)], delay_each=0.003)
    CACHE.set(f"out{out_n}_mode","quad")
    CACHE.set(f"out{out_n}_map",{1:1,2:2,3:3,4:4})

def ensure_map_cached(out_n: int):
    key = f"out{out_n}_map"; m = CACHE.get(key)
    if m: return m
    m = {}
    for w in range(1,5):
        rep = SER.send(C.q_window_in_source(out_n,w))
        m[w] = C.parse_hdmi_number(rep); sleep(0.02)
    CACHE.set(key, m); return m
