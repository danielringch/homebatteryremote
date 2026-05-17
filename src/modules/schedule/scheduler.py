import logging
from ..core import Triggers, OperationMode, app_state, EventPayload, triggers
from ..uplink.virtualcontroller import VirtualController

class Scheduler:
    def __init__(self, uplink: VirtualController):
        self.__uplink = uplink

        self.__mode_sent_count = 0
        self.__controllers_in_startup: set[str] = set()

        app_state.data.locks.on_change.subscribe(self.__locks_handler)
        app_state.data.schedule.on_change.subscribe(self.__get_requested_modes)
        app_state.data.manual_mode.on_change.subscribe(self.__get_requested_modes)
        app_state.data.requested_mode.on_change.subscribe(self.__send_mode)

    def start(self):
        self.__expand_and_send()
        triggers.add('update_schedule', '0/15 * * * *', self.__expand_and_send)

    def __expand_and_send(self):
        old_counter = self.__mode_sent_count
        app_state.expand_schedule()
        # the next step is only necessary on startup, since if the schedule did not change
        # the value of requested mode would still have its initial value
        self.__get_requested_modes()
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

            requested_mode = app_state.data.requested_mode.value.get(name)
            if not requested_mode:
                logging.warning(f'Statup of controller {name} detected, but no requested mode is available.')
                continue
        
            logging.info(f'Statup of controller {name} detected, sending mode {requested_mode.value} command again.')
            self.__uplink.send_mode(requested_mode, name)

    def __get_requested_modes(self, _ = None):
        requested_mode = app_state.data.schedule.value.get(Triggers.get_current_quarter_hour())
        manual_modes_by_controller = app_state.data.manual_mode.value

        requested_modes_by_controller: dict[str, OperationMode] = {}
        for controller in self.__uplink.mode_settable_controllers:
            # prio 1: manual mode
            # prio 2: schedule
            # prio 3: in case the schedule was not yet expanded, keep the last requested mode
            # prio 4: last resort: mode idle
            requested_modes_by_controller[controller] = manual_modes_by_controller.get(controller)\
                or requested_mode \
                or app_state.data.requested_mode.value.get(controller) \
                or OperationMode.IDLE
                
        app_state.data.requested_mode.set(requested_modes_by_controller)

    def __send_mode(self, _ = None):
        modes_by_controller = app_state.data.requested_mode.value
        for controller, mode in modes_by_controller.items():
            logging.info(f'Next mode for {controller}: {mode.value}.')
            self.__uplink.send_mode(mode, controller)
        self.__mode_sent_count = (self.__mode_sent_count + 1) & 0xFFFF
