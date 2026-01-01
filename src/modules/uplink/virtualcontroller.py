from collections.abc import Iterable
from copy import copy
from decimal import Decimal
from ..core import get_config_key, OperationMode, app_state, EventBox

from .mqtt import Mqtt
from .singlecontroller import SingleController, HOMEBATTERY_CONFIG_KEY



class VirtualController:
    def __init__(self, config, mqtt: Mqtt):
        raw_controllers = get_config_key(config, lambda x: (str(y) for y in x.keys()), None, HOMEBATTERY_CONFIG_KEY)

        self.__controllers: list[SingleController] = []
        for name in raw_controllers:
            controller = SingleController(config, mqtt, name)
            controller.subscribe_mode(self.__mode_handler)
            controller.subscribe_locked(self.__locked_handler)
            controller.subscribe_battery(self.__battery_data_handler)
            controller.subscribe_charger(self.__charger_data_handler)
            controller.subscribe_inverter(self.__inverter_data_handler)
            controller.subscribe_solar(self.__solar_data_handler)
            self.__controllers.append(controller)

        self.__modes_actual: dict[str, OperationMode | None] = {x.name: None for x in self.__controllers}
        app_state.data.actual_mode.set(copy(self.__modes_actual))
        self.__locks: dict[str, tuple[str, ...]] = {x.name: tuple() for x in self.__controllers}

        self.__capacities = AggregatedMessage(x.name for x in self.__controllers)
        self.__charger_energies = AggregatedMessage(x.name for x in self.__controllers)
        self.__inverter_energies = AggregatedMessage(x.name for x in self.__controllers)
        self.__solar_energies = AggregatedMessage(x.name for x in self.__controllers)

        self.__on_battery_capacity: EventBox[Decimal] = EventBox()
        self.__charger_energy_callback: EventBox[int] = EventBox()
        self.__inverter_energy_callback: EventBox[int] = EventBox()
        self.__solar_energy_callback: EventBox[int] = EventBox()

    @property
    def controllers(self):
        return tuple(x.name for x in self.__controllers)
    
    @property
    def mode_settable_controllers(self):
        return set(x.name for x in self.__controllers if x.is_mode_settable)
    
    @property
    def resettable_controllers(self):
        return set(x.name for x in self.__controllers if x.is_resettable)

    @property
    def modes_actual(self):
        return self.__modes_actual
    
    @property
    def locks(self):
        return self.__locks
    
    @property
    def on_battery_capacity(self):
        return self.__on_battery_capacity
    
    @property
    def on_charger_energy(self):
        return self.__charger_energy_callback
    
    @property
    def on_inverter_energy(self):
        return self.__inverter_energy_callback
    
    @property
    def on_solar_energy(self):
        return self.__solar_energy_callback

    def send_mode(self, mode: OperationMode, name: str | None = None):
        controllers = (x for x in self.__controllers if x.name == name) if name else self.__controllers
        for controller in controllers:
            controller.send_mode(mode)

    def send_reset(self, name: str | None = None):
        controllers = (x for x in self.__controllers if x.name == name) if name else self.__controllers
        for controller in controllers:
            controller.send_reset()

    def __mode_handler(self, sender: SingleController, mode: OperationMode):
        last_mode = self.__modes_actual.get(sender.name)
        if last_mode == mode:
            return
        self.__modes_actual[sender.name] = mode
        app_state.data.actual_mode.set(copy(self.__modes_actual))

    def __locked_handler(self, sender: SingleController, locks: list[str]):
        last_locks = self.__locks.get(sender.name)
        if last_locks == locks:
            return
        self.__locks[sender.name] = tuple(locks)
        app_state.data.locks.set(copy(self.__locks))
    
    def __battery_data_handler(self, sender: SingleController, capacity: Decimal):
        self.__capacities.add(sender.name, capacity)
        if (total_capacity := self.__capacities.try_get()) is not None:
            self.__on_battery_capacity.fire(self, total_capacity)

    def __charger_data_handler(self, sender: SingleController, energy: int | None):
        if energy is not None:
            self.__charger_energies.add(sender.name, energy)
            if (total_energy := self.__charger_energies.try_get()) is not None:
                self.__charger_energy_callback.fire(self, total_energy)

    def __inverter_data_handler(self, sender: SingleController, energy: int | None):
        if energy is not None:
            self.__inverter_energies.add(sender.name, energy)
            if (total_energy := self.__inverter_energies.try_get()) is not None:
                self.__inverter_energy_callback.fire(self, total_energy)

    def __solar_data_handler(self, sender: SingleController, energy: int | None):
        if energy is not None:
            self.__solar_energies.add(sender.name, energy)
            if (total_energy := self.__solar_energies.try_get()) is not None:
                self.__solar_energy_callback.fire(self, total_energy)

class AggregatedMessage:
    def __init__(self, senders: Iterable[str]):
        self.__senders = set(senders)
        self.__messages: dict[str, int | Decimal] = {} # key: sender; value: value

    @property
    def is_ready(self):
        return  not self.__senders.difference(self.__messages.keys())

    def add(self, sender: str, value: Decimal | int | None):
        if value is None:
            return
        self.__messages[sender] = value

    def try_get(self):
        if not self.is_ready:
            return None
        result = sum(self.__messages.values())
        self.__messages.clear()
        return result
