from typing import Callable
from typing import Dict
from typing import Generic
from typing import Hashable
from typing import List
from typing import Optional
from typing import TypeVar

T = TypeVar("T")
HashableT = TypeVar("HashableT", bound=Hashable)


class FastQueue(Generic[T]):
    """
    A queue implementation that does append(), next() and get_pos() in O(1)
    Limitations:
    - the queue has a fixed size of max elements it can maintain
    - the elements must be hashable or provide a hashable identifier as key
    -> Only elements that provide the same "hashable" interface, can be held in the same instance
    """

    def __init__(self, max_size: int = 32, key: Callable[[T], HashableT] = lambda elm: elm):
        """
        Args:
            max_size: the max size of elements that can be stored in the queue
            key: function to extract the hashable identifier (default is the element T itself)
        """
        # TODO: maybe use __hash__ instead of key

        self.__max_size = max_size
        # TODO: we could probably get away with just using the dicts own ordered structure
        #  with .pop() and __setitem__
        self.__queue: List[Optional[T]] = [None] * max_size
        self.__index_dict: Dict[HashableT, int] = {}
        self._key_fn = key

        self.__next_element_idx = 0  # points to the lobby next in queue ("pos 1 in queue")
        self.__next_free_index = 0
        self.current: T = None       # the current element that was returned by next()

    def put(self, elm: T):
        if len(self) == self.__max_size:
            raise OverflowError(f"The Queue is full: max size={self.__max_size}")

        self.__queue[self.__next_free_index] = elm
        self.__index_dict[self._key_fn(elm)] = self.__next_free_index

        if self.__next_free_index == self.__max_size - 1:
            self.__next_free_index = 0
        else:
            self.__next_free_index += 1

    def index(self, elm: T = None, by_key: HashableT = None) -> Optional[int]:
        if elm is not None and by_key is not None:
            raise ValueError(f"Use only 'elm' OR 'by_key', got: {elm=}, {by_key=}")

        if elm is not None:
            identifier = self._key_fn(elm)
        else:
            identifier = by_key

        # this element is not in the queue but the current one
        if self.current is not None and identifier == self._key_fn(self.current):
            return 0

        if identifier not in self.__index_dict:
            return None

        elm_index = self.__index_dict[identifier]

        queue_len = len(self)
        next_element_index = self.__next_element_idx

        # element is further back than next element
        if next_element_index <= elm_index:
            # +1 because next element is also waiting
            return elm_index - next_element_index + 1

        # element is located at a smaller index than next element (list wrapped one)
        else:
            # calculate how much is left till "end" of list
            # then plus element_index (from start of list to element)
            # +1 because next element is also waiting
            return self.__max_size - next_element_index + elm_index + 1

    def __next__(self) -> T:
        if len(self) == 0:
            raise StopIteration(f"No elements in queue")

        # extract
        elm = self.__queue[self.__next_element_idx]
        # delete entry
        self.__queue[self.__next_element_idx] = None

        # refresh index counter
        if self.__next_element_idx == self.__max_size - 1:
            self.__next_element_idx = 0
        else:
            self.__next_element_idx += 1

        # remove entry from index dict
        del self.__index_dict[self._key_fn(elm)]

        self.current = elm

        return elm

    def to_priority_dict(self) -> dict[int, T]:
        """
        read out the queue without emptying it
        indices are consistent with the sequential call of .index() and next()

        Returns:
            dict mapping index to element. first in queue is key 1, 0 is current element if exists
        """
        elm_list = [elm for elm in self.__queue if elm is not None]
        priority_dict = {}
        if self.current is not None:
            priority_dict[0] = self.current

        queued_element_priorities = {self.index(elm): elm for elm in elm_list}

        return {**priority_dict, **queued_element_priorities}

    def __len__(self) -> int:
        # our queue only holds as many keys as our dict has entries
        return len(self.__index_dict)

    def __repr__(self):
        return f"<FastQueue(queue={self.__queue}, idx_dict={self.__index_dict})>"


if __name__ == '__main__':
    fq = FastQueue(4)

    fq.put(1)
    fq.put(2)
    fq.put(3)
    fq.put(4)

    p = fq.index(2)
    print(p)

    print(fq.to_priority_dict())

    fq.__next__()
    print(fq.to_priority_dict())
    fq.__next__()
    print(fq.to_priority_dict())
    fq.put(5)

    p = fq.index(5)
    print(p)
