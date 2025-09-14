# services/state_cache.py
from time import time

class MatrixCache:
    def __init__(self):
        self.data = {}
        self.ts = {}
        self.featured_source = None
        self.out2_border_src = None
        self.last_sent = {}
        # NEW: track last highlighted window & color per output to avoid clears
        self.border_state = {
            1: {"window": None, "color": 2},  # default RED
            2: {"window": None, "color": 2},
        }

    def set(self, k, v):
        self.data[k] = v
        self.ts[k] = time()

    def get(self, k, max_age=None):
        if k not in self.data:
            return None
        if max_age is not None and (time() - self.ts.get(k, 0)) > max_age:
            return None
        return self.data[k]

    def clear(self, prefix=None):
        if prefix is None:
            self.data.clear()
            self.ts.clear()
        else:
            for k in list(self.data.keys()):
                if str(k).startswith(prefix):
                    self.data.pop(k, None)
                    self.ts.pop(k, None)

CACHE = MatrixCache()
