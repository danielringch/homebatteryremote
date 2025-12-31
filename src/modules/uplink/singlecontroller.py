import json, logging
from decimal import Decimal
from ..core import get_config_key, get_optional_config_key, OperationMode

from .mqtt import Mqtt

HOMEBATTERY_CONFIG_KEY = 'homebattery'
_ROOT_CONFIG_KEY = 'root'
_IS_MODE_SETTABLE_CONFIG_KEY = 'is_mode_settable'
_IS_RESETTABLE_CONFIG_KEY = 'is_resettable'

class SingleController:
    def __init__(self, config: dict, mqtt: Mqtt, name: str):
        self.__mqtt = mqtt
        self.__name = name
        self.__root = get_config_key(config, str, None, HOMEBATTERY_CONFIG_KEY, name, _ROOT_CONFIG_KEY)
        self.__is_mode_settable = get_optional_config_key(config, bool, True, None, HOMEBATTERY_CONFIG_KEY, name, _IS_MODE_SETTABLE_CONFIG_KEY)
        self.__is_resettable = get_optional_config_key(config, bool, True, None, HOMEBATTERY_CONFIG_KEY, name, _IS_RESETTABLE_CONFIG_KEY)

        self.__mode_set_topic = f'{self.__root}/mode/set'
        self.__reset_topic = f'{self.__root}/reset'

        mqtt.subscribe(f'{self.__root}/mode/actual', 1, self.__on_mode_actual)
        mqtt.subscribe(f'{self.__root}/locked', 1, self.__on_locked)
        mqtt.subscribe(f'{self.__root}/cha/sum', 2, self.__on_charger)
        mqtt.subscribe(f'{self.__root}/inv/sum', 2, self.__on_inverter)
        mqtt.subscribe(f'{self.__root}/sol/sum', 2, self.__on_solar)
        mqtt.subscribe(f'{self.__root}/bat/sum', 2, self.__on_battery)

        self.__mode_callback = None
        self.__locked_callback = None
 
        self.__battery_callback = None
        self.__charger_callback = None
        self.__inverter_callback = None
        self.__solar_callback = None

    @property
    def name(self):
        return self.__name
    
    @property
    def is_mode_settable(self):
        return self.__is_mode_settable
    
    @property
    def is_resettable(self):
        return self.__is_resettable

    def send_mode(self, mode: OperationMode):
        if not self.__is_mode_settable:
            return
        self.__mqtt.publish(self.__mode_set_topic, mode.value.encode('utf-8'), qos=1, retain=False)

    def send_reset(self):
        if not self.__is_resettable:
            return
        self.__mqtt.publish(self.__reset_topic, 'reset'.encode('utf-8'), qos=1, retain=False)

    def subscribe_mode(self, callback):
        self.__mode_callback = callback

    def subscribe_locked(self, callback):
        self.__locked_callback = callback

    def subscribe_battery(self, callback):
        self.__battery_callback = callback

    def subscribe_charger(self, callback):
        self.__charger_callback = callback

    def subscribe_inverter(self, callback):
        self.__inverter_callback = callback

    def subscribe_solar(self, callback):
        self.__solar_callback = callback

    def __on_mode_actual(self, msg):
        string = msg.payload if isinstance(msg.payload, str) else msg.payload.decode('utf-8')
        try:
            mode = OperationMode(string)
        except:
            mode = None
        logging.debug(f'MQTT {self.__root}: Operation mode: {string}.')
        if self.__mode_callback:
            self.__mode_callback(self, mode)

    def __on_locked(self, msg):
        locks = sorted(json.loads(msg.payload.decode('utf-8'))) or []
        logging.debug(f'MQTT {self.__root}: Locks: {", ".join(locks or ("<none>",))}.')
        if self.__locked_callback:
            self.__locked_callback(self, locks)

    def __on_battery(self, msg):
        try:
            raw_data = json.loads(msg.payload.decode('utf-8'))
            capacity = round(Decimal(raw_data['capacity']), 1)
        except:
            logging.warning(f'MQTT {self.__root}: Can not parse battery message.')
            return
        logging.debug(f'MQTT {self.__root}: Combined battery capacity: {capacity} Ah.')
        if self.__battery_callback:
            self.__battery_callback(self, capacity)

    def __on_charger(self, msg):
        self.__parse_sum_message(msg, 'charger', self.__charger_callback)

    def __on_inverter(self, msg):
        self.__parse_sum_message(msg, 'inverter', self.__inverter_callback)

    def __on_solar(self, msg):
        self.__parse_sum_message(msg, 'solar', self.__solar_callback)

    def __parse_sum_message(self, msg, sender: str, callback):
        try:
            raw_data = json.loads(msg.payload.decode('utf-8'))
            raw_energy = raw_data.get('energy')
            energy = int(raw_energy) if (raw_energy is not None) else None
        except:
            logging.warning(f'MQTT {self.__root}: Can not parse {sender} message.')
            return
        if (energy is None):
            return
        logging.debug(f'MQTT {self.__root}: {sender} data: energy={energy} Wh.')
        if callback:
            callback(self, energy)
