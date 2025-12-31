from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Callable

T = TypeVar('T')

@dataclass
class EventPayload(Generic[T]):
    sender: Any
    data: T

@dataclass
class _EventSubscription(Generic[T]):
    id: int | str | None
    callback: Callable[[EventPayload[T]], None]

class EventBox(Generic[T]):
    PRE = 1
    NORMAL = 2
    POST = 3

    def __init__(self):
        self.__callbacks: tuple[list[_EventSubscription[T]], ...] = ([], [], [])

    def subscribe(self, callback: Callable[[EventPayload[T]], None], id: int | str | None = None, prio=NORMAL):
        self.__callbacks[prio].append(_EventSubscription(id, callback))

    def unsubscribe_by_id(self, id: str | int):
        for prio in self.__callbacks:
            for i in range(len(prio) - 1, -1, -1):
                if prio[i].id == id:
                    del prio[i]

    def fire(self, sender: Any, data: T):
        payload = EventPayload(sender, data)
        for prio in self.__callbacks:
            for subscription in prio:
                subscription.callback(payload)
