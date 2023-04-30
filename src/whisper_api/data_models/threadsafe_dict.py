import collections
import threading

# it's a shame that this is not in the standard library...
# I wanna thank ChatGPT for making the pain less painful


class ThreadSafeDict(collections.defaultdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.default_factory = None

    def __getitem__(self, key):
        with self.lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self.lock:
            return super().__setitem__(key, value)

    def __delitem__(self, key):
        with self.lock:
            return super().__delitem__(key)

    def __contains__(self, key):
        with self.lock:
            return super().__contains__(key)

    def __len__(self):
        with self.lock:
            return super().__len__()

    def __iter__(self):
        with self.lock:
            return super().__iter__()

    def __repr__(self):
        with self.lock:
            return super().__repr__()

    def __str__(self):
        with self.lock:
            return super().__str__()

    def __copy__(self):
        with self.lock:
            return super().__copy__()

    def copy(self):
        with self.lock:
            return super().copy()
