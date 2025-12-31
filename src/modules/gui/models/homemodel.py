from ...core import OperationMode, app_state
from ..singletons import singletons
from .modeltypes import BindableValue, BridgedValue


class HomeControllerState:
    def __init__(self, mode_actual: str = '', mode_control_type: str = '', locks: str = ''):
        self.mode_actual = BindableValue(mode_actual)
        self.mode_control_type = BindableValue(mode_control_type)
        self.locks = BindableValue(locks)

class HomeModel:
    def __init__(self, id: str):
        self.__id = id

        system = singletons.virtual_controller

        self.requested_mode = BridgedValue(id, app_state.data.requested_mode, lambda x: x.value)
        self.manual_mode = BridgedValue(id, app_state.data.manual_mode, lambda x: x)

        self.controller_states = {name: HomeControllerState() for name in system.controllers}

        self.__mode_actual_change_handler()
        app_state.data.actual_mode.on_change.subscribe(self.__mode_actual_change_handler, id=id)

        self.__manual_mode_change_handler()
        app_state.data.manual_mode.on_change.subscribe(self.__manual_mode_change_handler, id=id)

        self.__locks_change_handler()
        app_state.data.locks.on_change.subscribe(self.__locks_change_handler, id=id)

    def destroy(self):
        self.requested_mode.destroy()
        self.manual_mode.destroy()
        app_state.data.actual_mode.on_change.unsubscribe_by_id(self.__id)
        app_state.data.manual_mode.on_change.unsubscribe_by_id(self.__id)
        app_state.data.locks.on_change.unsubscribe_by_id(self.__id)

    def __mode_actual_change_handler(self, _ = None):
        for name, mode in app_state.data.actual_mode.value.items():
            self.controller_states[name].mode_actual.set(self.__print_mode(mode))

    def __manual_mode_change_handler(self, _ = None):
        mode = app_state.data.manual_mode.value
        system = singletons.virtual_controller
        for name in system.controllers:
            if name not in system.mode_settable_controllers:
                type_ = 'readonly'
            else:
                type_ = 'manual' if bool(mode) else 'schedule'
            self.controller_states[name].mode_control_type.set(type_)

    def __locks_change_handler(self, _ = None):
        all_locks = app_state.data.locks.value
        system = singletons.virtual_controller
        for name in system.controllers:
            locks = all_locks.get(name)
            if locks is None:
                locks_str = '(unknown)'
            else:
                locks_str = '\n'.join(sorted(locks)) or '(none)'
            self.controller_states[name].locks.set(locks_str)

    @staticmethod
    def __print_mode(value: OperationMode | None):
        return '(unknown)' if (value is None) else value.value
