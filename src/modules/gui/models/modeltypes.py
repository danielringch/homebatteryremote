from nicegui import binding
from typing import Generic, TypeVar, Callable
from ...core import AppStateValue, EventPayload

T = TypeVar('T')
TIn = TypeVar('TIn')
TOut= TypeVar('TOut')

class BindableValue(Generic[T]):
    value = binding.BindableProperty()

    def __init__(self, value: T):
        self.value = value

    def set(self, value):
        self.value = value

class BridgedValue(Generic[TIn, TOut]):
    value = binding.BindableProperty()

    def __init__(self, id: str, source: AppStateValue[TIn], cast: Callable[[TIn], TOut]):
        self.__id = id
        self.value = cast(source.value)
        self.__cast = cast
        self.__source = source
        source.on_change.subscribe(self.__source_value_change_handler, id=id)

    def destroy(self):
        self.__source.on_change.unsubscribe_by_id(self.__id)
        self.__source = None

    def __source_value_change_handler(self, args: EventPayload[TIn]):
        self.value = self.__cast(args.data)
