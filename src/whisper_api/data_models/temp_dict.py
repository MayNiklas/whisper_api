import threading
import time
from collections import defaultdict
from typing import TypeVar, Iterable, Optional, MutableMapping, Iterator, Union

"""
Threadsafe DataStructure that holds data for a given time and then discards it

I really tried to make this thing generic.
I hope it's the correct way to do it...
"""


Identifier_t = TypeVar('Identifier_t')
Value_t = TypeVar('Value_t')

creation_time_t = float


class TempDict(MutableMapping[Identifier_t, Value_t]):

    def __init__(self, expiration_time_m=30,
                 refresh_expiration_time_on_usage=True,
                 auto_gc_interval_s=60):
        """
        Args:
            expiration_time_m: time in minutes after which an item is considered expired
            refresh_expiration_time_on_usage: reset countdown if item is accessed
            auto_gc_interval_s: time between automatic garbage collection runs if None gc runs before each operation
        """
        self.lock = threading.RLock()
        self.__data: dict[Identifier_t, list[creation_time_t, Value_t]] = defaultdict(None)
        self.expiration_time_s: int = expiration_time_m * 60
        if expiration_time_m <= 0:
            raise ValueError("Expiration time must be greater than 0")
        self.refresh_expiration_time_on_usage = refresh_expiration_time_on_usage

        self.auto_gc_interval_s = auto_gc_interval_s
        self.lazy_expiry_checker = self.ExpirationChecker(self)
        if auto_gc_interval_s:
            self.start_auto_gc()

    def start_auto_gc(self):
        """ Start thread that cleans up in given interval """
        def cleaner():
            """ Cleaner with adapting interval if value is changed """
            self._clean_expired_items()
            time.sleep(self.auto_gc_interval_s)

        threading.Thread(target=cleaner, daemon=True).start()

    class ExpirationChecker:
        """ Context manager that triggers a gc when no auto_gc_interval is set """
        def __init__(self, parent: 'TempDict', force_check=False):
            self.parent = parent
            self.force_check = force_check

        def __enter__(self):
            if self.force_check or not self.parent.auto_gc_interval_s:
                self.parent._clean_expired_items()

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    """
    Properties, Getters & Variable-Setters
    
    If they work on data they'll always trigger an expiration check
    to ensure that only non-timed-out data is used
    """

    @property
    def expiration_time_m(self) -> int:
        return self.expiration_time_s // 60

    @expiration_time_m.setter
    def expiration_time_m(self, value: int):
        self.expiration_time_s = value * 60

    @property
    def expand_lifespan_on_usage_m(self) -> int:
        return self.expiration_time_s // 60

    @expand_lifespan_on_usage_m.setter
    def expand_lifespan_on_usage_m(self, value: int):
        self.expiration_time_s = value * 60

    @property
    def size(self) -> int:
        """ number of items in datastructure """
        with self.lock:
            self._clean_expired_items()
            return self.__data.__len__()

    @property
    def speed(self) -> int:
        """ items per second averaged over expiration time"""
        with self.lock:
            self._clean_expired_items()
            return self.__data.__len__() // self.expiration_time_s

    @property
    def current_data(self):
        with self.lock:
            self._clean_expired_items()
            return {key: value for key, (time_out, value) in self.__data.items()}

    def __len__(self) -> int:
        with self.lock:
            self._clean_expired_items()
            return len(self.__data)

    def __iter__(self) -> Iterator[Identifier_t]:
        with self.lock:
            self._clean_expired_items()
            return self.__data.__iter__()

    def __getitem__(self, key: Identifier_t) -> Optional[Value_t]:
        """ Returns None if key is not found """
        with self.lock:
            self._clean_expired_items()

            # test if key is entered
            val = self.__data[key]
            if val is None:
                return None

            if self.refresh_expiration_time_on_usage:
                self.__extend_lifespan(key)

            return val[1]

    """
    Setters
    Setters only trigger an expiration check when no gc-thread is started
    """

    def __setitem__(self, identifier: Identifier_t, value: Value_t) -> None:
        """ Just add an item without any expiration checks, not expanding liespan if item already exists """
        with self.lock, self.lazy_expiry_checker:
            self.__add_item(identifier, value, extend_lifespan_if_exists=False)

    def add_item(self,
                 identifier: Identifier_t,
                 value: Value_t,
                 extend_lifespan_if_exists=True):
        """ Add item, expand lifespan if it already exists and trigger expiration checks """
        with self.lock, self.lazy_expiry_checker:
            # check if items shall also be refreshed or just added if new
            if not extend_lifespan_if_exists and identifier in self.__data.keys():
                return

            self.__add_item(identifier,
                            value,
                            extend_lifespan_if_exists=extend_lifespan_if_exists)

    def add_items(self,
                  items: Iterable[Union[tuple[Identifier_t, Value_t], list[Identifier_t, Value_t]]],
                  extend_lifespan_if_exists=True):
        """ Add multiple items without expiration checks """
        # TODO maybe allow for manual overwrite of expiry time expansion
        with self.lock, self.lazy_expiry_checker:
            for key, value in items:
                self.__add_item(key, value, extend_lifespan_if_exists=extend_lifespan_if_exists)

    def extend_lifespan(self, key: Identifier_t, expiration_time_overwrite_m: float = None):
        """ Extend lifespan of item and trigger expiration checks """
        if expiration_time_overwrite_m is None and not self.refresh_expiration_time_on_usage:
            raise ValueError("Lifetime extension is not enabled by default and overwrite time is not given")

        with self.lock, self.lazy_expiry_checker:
            self.__extend_lifespan(key, expiration_time_overwrite_m * 60)

    def __delitem__(self, key: Identifier_t):
        """ Does not trigger expiration checks """
        with self.lock, self.lazy_expiry_checker:
            if key not in self.__data.keys():
                return

            del self.__data[key]

    def remove_item(self, item: Identifier_t):
        """ Remove item and trigger expiration checks """
        with self.lock, self.lazy_expiry_checker:
            self.__delitem__(item)

    """ Internal helpers """

    def _clean_expired_items(self):
        """ Garbage collector that removes expired items """
        with self.lock:
            now = time.time()
            keys_to_remove = []
            for key, (timestamp, _) in self.__data.items():
                if now - timestamp > self.expiration_time_s:
                    keys_to_remove.append(key)
                else:
                    break

            for key in keys_to_remove:
                del self.__data[key]

    def __add_item(self, identifier: Identifier_t, value: Value_t, extend_lifespan_if_exists: bool):
        """ Non-thread safe internal add item, not triggering gc """
        # when item in dict and extend lifespan is enabled, just extend lifespan
        if extend_lifespan_if_exists and identifier in self.__data.keys():
            self.__extend_lifespan(identifier)
            return

        # truly add new item
        now = time.time()
        self.__data[identifier] = [now, value]

    def __extend_lifespan(self, key: Identifier_t, expiration_time_overwrite_s: float = None):
        """ Not thread safe, not checking for gc """
        # if no expansion time is given at all return
        if not (self.refresh_expiration_time_on_usage or expiration_time_overwrite_s):
            return

        val = self.__data[key]
        if val is None:
            return

        # expand only by given timespan
        if expiration_time_overwrite_s:
            val[0] = val[0] + expiration_time_overwrite_s

        # reset time
        val[0] = time.time()


if __name__ == '__main__':

    # Example usage:
    temp_store = TempDict(expiration_time_m=5)  # retention time in seconds

    temp_store.add_item('item1')
    temp_store.add_item('item2')
    print(temp_store.size)  # prints 2
    time.sleep(6)  # wait for 6 seconds
    print(temp_store.size)  # prints 0 (items have expired)
    print(temp_store.current_data)
    d = dict()
