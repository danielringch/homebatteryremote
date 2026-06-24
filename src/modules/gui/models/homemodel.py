from ...core import OperationMode, app_state
from ..singletons import singletons
from .modeltypes import BindableValue


class HomeControllerState:
    def __init__(self):
        self.mode_manual: BindableValue[OperationMode | None] = BindableValue(None) # None mean not mode settable
        self.mode_requested = BindableValue('')
        self.mode_actual = BindableValue('')
        self.mode_control_type = BindableValue('')
        self.locks = BindableValue('')


class HomeModel:
    def __init__(self, id: str):
        self.__id = id

        self.controller_states = {name: HomeControllerState() for name in singletons.virtual_controller.controllers}

        self.__manual_mode_change_handler()
        app_state.data.manual_mode.on_change.subscribe(self.__manual_mode_change_handler, id=id)

        self.__requested_mode_change_handler()
        app_state.data.requested_mode.on_change.subscribe(self.__requested_mode_change_handler, id=id)

        self.__mode_actual_change_handler()
        app_state.data.actual_mode.on_change.subscribe(self.__mode_actual_change_handler, id=id)

        self.__locks_change_handler()
        app_state.data.locks.on_change.subscribe(self.__locks_change_handler, id=id)

    def destroy(self):
        app_state.data.manual_mode.on_change.unsubscribe_by_id(self.__id)
        app_state.data.requested_mode.on_change.unsubscribe_by_id(self.__id)
        app_state.data.actual_mode.on_change.unsubscribe_by_id(self.__id)
        app_state.data.locks.on_change.unsubscribe_by_id(self.__id)

    def __manual_mode_change_handler(self, _ = None):
        mode_by_controller = app_state.data.manual_mode.value
        for name in singletons.virtual_controller.controllers:
            if name not in singletons.virtual_controller.mode_settable_controllers:
                manual_mode = None
                control_type = 'readonly'
            else:
                manual_mode = mode_by_controller.get(name)
                control_type = 'manual' if bool(manual_mode) else 'schedule'
            self.controller_states[name].mode_manual.set(manual_mode)
            self.controller_states[name].mode_control_type.set(control_type)

    def __requested_mode_change_handler(self, _ = None):
        mode_by_controller = app_state.data.requested_mode.value
        for name in singletons.virtual_controller.controllers:
            if name not in singletons.virtual_controller.mode_settable_controllers:
                requested_mode = '(none)'
            else:
                requested_mode = mode_by_controller.get(name)
            self.controller_states[name].mode_requested.set(requested_mode)

    def __mode_actual_change_handler(self, _ = None):
        for name, mode in app_state.data.actual_mode.value.items():
            self.controller_states[name].mode_actual.set(self.__print_mode(mode))

    def __locks_change_handler(self, _ = None):
        locks_by_controller = app_state.data.locks.value
        for name in singletons.virtual_controller.controllers:
            locks = locks_by_controller.get(name)
            if locks is None:
                locks_str = '(unknown)'
            else:
                locks_str = '\n'.join(sorted(locks)) or '(none)'
            self.controller_states[name].locks.set(locks_str)

    @staticmethod
    def __print_mode(value: OperationMode | None):
        return '(unknown)' if (value is None) else value.value
