import logging
from collections import namedtuple
from ..core import Triggers, OperationMode, app_state, EventPayload
from ..uplink.virtualcontroller import VirtualController

class Scheduler:
    ScheduleEntry = namedtuple('ScheduleEntry', 'timestamp mode')

    def __init__(self, uplink: VirtualController):
        self.__uplink = uplink

        self.__controllers_in_startup: set[str] = set()

        app_state.data.locks.on_change.subscribe(self.__locks_handler)
        app_state.data.schedule.on_change.subscribe(self.__get_requested_mode)
        app_state.data.manual_mode.on_change.subscribe(self.__get_requested_mode)
        app_state.data.requested_mode.on_change.subscribe(self.__requested_mode_change_handler)

    def start(self):
        self.__get_requested_mode()
        self.__requested_mode_change_handler(EventPayload(None, app_state.data.requested_mode.value))

    def __locks_handler(self, args: EventPayload[dict[str, tuple[str, ...]]]):
        for name, locks in args.data.items():
            if name not in self.__uplink.mode_settable_controllers:
                continue
            if 'startup' not in locks:
                self.__controllers_in_startup.discard(name)
                continue
            if name in self.__controllers_in_startup:
                continue
        
            self.__controllers_in_startup.add(name)
            requested_mode: OperationMode = app_state.data.requested_mode.value
            logging.info(f'Statup of controller {name} detected, sending mode {requested_mode.value} command again.')
            self.__uplink.send_mode(requested_mode, name)

    def __get_requested_mode(self, _ = None):
        manual_mode = app_state.data.manual_mode.value
        if manual_mode:
            requested_mode = manual_mode
        else:
            schedule = app_state.data.schedule.value
            requested_mode = schedule[Triggers.get_current_quarter_hour()]
        app_state.data.requested_mode.set(requested_mode)

    def __requested_mode_change_handler(self, args: EventPayload[OperationMode]):
        self.__uplink.send_mode(args.data)
        logging.info(f'Next mode: {args.data.value}.')
