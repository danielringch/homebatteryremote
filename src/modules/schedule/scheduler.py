import logging
from collections import namedtuple
from ..core import Triggers, OperationMode, app_state, EventPayload, triggers
from ..uplink.virtualcontroller import VirtualController

class Scheduler:
    ScheduleEntry = namedtuple('ScheduleEntry', 'timestamp mode')

    def __init__(self, uplink: VirtualController):
        self.__uplink = uplink

        self.__mode_sent_count = 0
        self.__controllers_in_startup: set[str] = set()

        app_state.data.locks.on_change.subscribe(self.__locks_handler)
        app_state.data.schedule.on_change.subscribe(self.__get_requested_mode)
        app_state.data.manual_mode.on_change.subscribe(self.__get_requested_mode)
        app_state.data.requested_mode.on_change.subscribe(self.__send_mode)

    def start(self):
        self.__expand_and_send()
        triggers.add('update_schedule', '0/15 * * * *', self.__expand_and_send)

    def __expand_and_send(self):
        old_counter = self.__mode_sent_count
        app_state.expand_schedule()
        # the next step is only necessary in startup, since if the schedule did not change
        # the value of requested mode would still have its initial value
        self.__get_requested_mode()
        # requested mode might get updated and sent automatically via event handlers
        if self.__mode_sent_count == old_counter:
            # no mode was sent since requested mode did not change, so send manually
            self.__send_mode()

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
            # it is not always quaranteed that the schedule is already expanded; so if not, assume that the last requested
            # mode is still valid
            requested_mode = schedule.get(Triggers.get_current_quarter_hour(), app_state.data.requested_mode.value)
        app_state.data.requested_mode.set(requested_mode)

    def __send_mode(self, _ = None):
        mode = app_state.data.requested_mode.value
        self.__uplink.send_mode(mode)
        logging.info(f'Next mode: {mode.value}.')
        self.__mode_sent_count = (self.__mode_sent_count + 1) & 0xFFFF
