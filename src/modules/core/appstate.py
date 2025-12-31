import json, os, base64, logging
from argon2 import PasswordHasher
from argon2 import Type as ArgonType
from collections.abc import Iterable
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO
from shutil import copyfileobj
from typing import Generic, TypeVar, Callable, Any

from .eventbox import EventBox
from .types import OperationMode
from .config import get_optional_config_key, get_config_key
from .triggers import Triggers, triggers

_INSTANCE_NAME_CONFIG_KEY = 'name'

ENERGY_CONFIG_KEY = 'energy'
_CHARGER_EFFICIENCY_CONFIG_KEY = 'charger_efficiency_factor'
_INVERTER_EFFICIENCY_CONFIG_KEY = 'inverter_efficiency_factor'
_MINIMUM_MARGIN_CONFIG_KEY = 'minimum_margin'

WEB_CONFIG_KEY = 'web'
_ADMIN_USER_CONFIG_KEY = 'admin_user'
_ADMIN_PASS_CONFIG_KEY = 'admin_password'
_USER_USER_CONFIG_KEY = 'user_user'
_USER_PASS_CONFIG_KEY = 'user_password'

_TIBBER_CONFIG_KEY = 'tibber'
_TIBBER_TOKEN_CONFIG_KEY = 'token'

_INSTANCE_NAME_ENV_NAME = 'BHRE_NAME'
_ADMIN_USER_ENV_NAME = 'HBRE_ADMIN_USER'
_ADMIN_PASS_ENV_NAME = 'HBRE_ADMIN_PASSWORD'
_USER_USER_ENV_NAME = 'HBRE_USER_USER'
_USER_PASS_ENV_NAME = 'HBRE_USER_PASSWORD'
_TIBBER_TOKEN_ENV_NAME = 'HBRE_TIBBER_TOKEN'

_AVG_CHARGED_PRICE_DATA_KEY = 'avg_charged_price'
_CONFIG_DATA_KEY = 'config'
_MANUAL_MODE_DATA_KEY = 'manual_mode'
_SCHEDULE_TEMPLATE_DATA_KEY = 'schedule_template'
_SCHEDULE_DATA_KEY = 'schedule'

SCHEDULE_TEMPLATE_LENGTH = 24 * 4
SCHEDULE_LENGTH = 48 * 4

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, encoding='utf-8', type=ArgonType.ID)

T = TypeVar('T')

class AppStateValue(Generic[T]):
    def __init__(self, file_data: dict, default: T, keys: tuple[str, ...], importer: Callable[[Any], T], exporter: Callable[[T], Any]):
        self.__file_data = file_data
        self.__keys: tuple[str, ...] = keys
        self.value = default
        self.on_change: EventBox[T] = EventBox()
        self.is_readonly = False
        self.__importer = importer
        self.__exporter = exporter

    @property
    def importer(self):
        return self.__importer

    def add_from_config(self, value: T | None):
        if value is None:
            return
        self.__set(value)
        self.is_readonly = True
        
    def add_from_file(self):
        if self.is_readonly or not self.__keys:
            return
        value = get_optional_config_key(self.__file_data, self.__importer, None, None, *self.__keys)
        if value is None:
            return
        self.value = value

    def set(self, value: T):
        if self.is_readonly:
            return
        self.__set(value)
        if not self.__keys:
            return
        
        dict = self.__get_leaf_dict()
        last_key = self.__keys[-1]
        if (export_value := self.__exporter(value)) is not None:
            dict[last_key] = export_value
        else:
            dict.pop(last_key, None)

    def __set(self, value: T):
        if self.is_readonly:
            return
        self.value = value
        self.on_change.fire(self, value)

    def __get_leaf_dict(self):
        dict = self.__file_data
        for key in self.__keys[:-1]:
            if (next_dict := dict.get(key)) is None:
                next_dict = {}
                dict[key] = next_dict
            dict = next_dict
        return dict

@dataclass
class AppStateMembers:
    actual_mode: AppStateValue[dict[str, OperationMode | None]]
    admin_pass: AppStateValue[str]
    admin_user: AppStateValue[str]
    avg_charged_price: AppStateValue[Decimal]
    charger_efficiency: AppStateValue[Decimal]
    instance_name: AppStateValue[str]
    inverter_efficiency: AppStateValue[Decimal]
    locks: AppStateValue[dict[str, tuple[str, ...]]]
    manual_mode: AppStateValue[OperationMode | None]
    minimum_margin: AppStateValue[Decimal]
    prices_revision: AppStateValue[datetime]
    remaining_capacity: AppStateValue[Decimal | None]
    requested_mode: AppStateValue[OperationMode]
    schedule: AppStateValue[dict[datetime, OperationMode]]
    template: AppStateValue[tuple[OperationMode, ...]]
    tibber_token: AppStateValue[str | None]
    user_pass: AppStateValue[str]
    user_user: AppStateValue[str]

class AppState:
    def __init__(self):
        self.__secret = ''
        self.__file = None
        self.__file_data = {}

        self.__data = AppStateMembers(
            actual_mode=AppStateValue(self.__file_data, {}, tuple(), None, None),
            admin_pass=AppStateValue(self.__file_data, '', (_CONFIG_DATA_KEY, WEB_CONFIG_KEY, _ADMIN_PASS_CONFIG_KEY), str, str),
            admin_user=AppStateValue(self.__file_data, 'admin', (_CONFIG_DATA_KEY, WEB_CONFIG_KEY, _ADMIN_USER_CONFIG_KEY), str, str),
            avg_charged_price=AppStateValue(self.__file_data, Decimal(0), (_AVG_CHARGED_PRICE_DATA_KEY,), lambda x: round(Decimal(x), 10), str),
            charger_efficiency=AppStateValue(self.__file_data, Decimal(1), (_CONFIG_DATA_KEY, ENERGY_CONFIG_KEY, _CHARGER_EFFICIENCY_CONFIG_KEY), lambda x: round(Decimal(x), 3), str),
            instance_name=AppStateValue(None, {}, tuple(), None, None),
            inverter_efficiency=AppStateValue(self.__file_data, Decimal(1), (_CONFIG_DATA_KEY, ENERGY_CONFIG_KEY, _INVERTER_EFFICIENCY_CONFIG_KEY), lambda x: round(Decimal(x), 3), str),
            locks=AppStateValue(None, {}, tuple(), None, None),
            manual_mode=AppStateValue(self.__file_data, None, (_MANUAL_MODE_DATA_KEY,), self.__import_manual_mode, self.__export_manual_mode),
            minimum_margin=AppStateValue(self.__file_data, Decimal(0), (_CONFIG_DATA_KEY, ENERGY_CONFIG_KEY, _MINIMUM_MARGIN_CONFIG_KEY), lambda x: round(Decimal(x), 4), str),
            prices_revision=AppStateValue(None, datetime.min, tuple(), None, None),
            remaining_capacity=AppStateValue(None, Decimal(-1), tuple(), None, None),
            requested_mode=AppStateValue(None, OperationMode.IDLE, tuple(), None, None),
            schedule=AppStateValue(self.__file_data, {}, (_SCHEDULE_DATA_KEY,), self.__import_schedule, self.__export_schedule),
            template=AppStateValue(self.__file_data, [], (_SCHEDULE_TEMPLATE_DATA_KEY,), self.__import_template, self.__export_template),
            tibber_token=AppStateValue(self.__file_data, None, (_CONFIG_DATA_KEY, _TIBBER_CONFIG_KEY, _TIBBER_TOKEN_CONFIG_KEY), self.__decrypt, self.__encrypt),
            user_pass=AppStateValue(self.__file_data, '', (_CONFIG_DATA_KEY, WEB_CONFIG_KEY, _USER_PASS_CONFIG_KEY), str, str),
            user_user=AppStateValue(self.__file_data, 'user', (_CONFIG_DATA_KEY, WEB_CONFIG_KEY, _USER_USER_CONFIG_KEY), str, str)
        )

    @property
    def data(self):
        return self.__data

    def load_config(self, secret: str, config: dict):
        self.__secret = secret
        self.__data.admin_pass.add_from_config(get_optional_config_key(config, str, None, _ADMIN_PASS_ENV_NAME, WEB_CONFIG_KEY, _ADMIN_PASS_CONFIG_KEY))
        self.__data.admin_user.add_from_config(get_optional_config_key(config, str, None, _ADMIN_USER_ENV_NAME, WEB_CONFIG_KEY, _ADMIN_USER_CONFIG_KEY))
        self.__data.charger_efficiency.add_from_config(get_optional_config_key(config, lambda x: round(Decimal(x), 3), None, None, ENERGY_CONFIG_KEY, _CHARGER_EFFICIENCY_CONFIG_KEY))
        self.__data.instance_name.add_from_config(get_config_key(config, str, _INSTANCE_NAME_ENV_NAME, _INSTANCE_NAME_CONFIG_KEY))
        self.__data.inverter_efficiency.add_from_config(get_optional_config_key(config, lambda x: round(Decimal(x), 3), None, None, ENERGY_CONFIG_KEY, _INVERTER_EFFICIENCY_CONFIG_KEY))
        self.__data.minimum_margin.add_from_config(get_optional_config_key(config, lambda x: round(Decimal(x), 4), None, None, ENERGY_CONFIG_KEY, _MINIMUM_MARGIN_CONFIG_KEY))
        self.__data.tibber_token.add_from_config(get_optional_config_key(config, self.__decrypt, None, _TIBBER_TOKEN_ENV_NAME, _TIBBER_CONFIG_KEY, _TIBBER_TOKEN_CONFIG_KEY))
        self.__data.user_pass.add_from_config(get_optional_config_key(config, str, None, _USER_PASS_ENV_NAME, WEB_CONFIG_KEY, _USER_PASS_CONFIG_KEY))
        self.__data.user_user.add_from_config(get_optional_config_key(config, str, None, _USER_USER_ENV_NAME, WEB_CONFIG_KEY, _USER_USER_CONFIG_KEY))

    def load_file(self, file: str):
        self.__file = file
        self.__file_data.clear()
        if os.path.exists(self.__file):
            with open(self.__file, 'r') as stream:
                self.__file_data.update(json.load(stream))

        for field in fields(AppStateMembers):
            getattr(self.__data, field.name).add_from_file()

    def start(self):
        self.__expand_template()
        self.__expand_schedule()
        triggers.add('update_schedule', '0/15 * * * *', self.__expand_schedule)

    def save(self):
        assert self.__file is not None
        with StringIO() as mem_stream:
            try:
                json.dump(self.__file_data, mem_stream, indent=4, sort_keys=True)
            except Exception as e:
                logging.error('Can not serialize app state: {e}')
                return
            try:
                with open(self.__file, 'w') as stream:
                    mem_stream.seek(0)
                    copyfileobj(mem_stream, stream)
            except Exception as e:
                logging.error(f'Can not write app state to file: {e}')

    def __expand_schedule(self):
        cutoff = Triggers.get_current_quarter_hour()
        schedule: dict[datetime, OperationMode] = {x: y for x, y in self.__data.schedule.value.items() if x >= cutoff}
        template: list[OperationMode] = self.__data.template.value

        timestamp = cutoff
        for _ in range(SCHEDULE_LENGTH):
            if timestamp not in schedule:
                schedule[timestamp] = template[self.__get_schedule_template_index(timestamp)]
            timestamp += timedelta(minutes=15)

        self.__data.schedule.set(schedule)

    def __expand_template(self):
        template = list(self.__data.template.value)
        for _ in range(SCHEDULE_TEMPLATE_LENGTH - len(template)):
            template.append(OperationMode.IDLE)
        self.__data.template.set(tuple(template[:SCHEDULE_TEMPLATE_LENGTH]))

    def __encrypt(self, plain: str | None):
        if not plain:
            return plain
        salt = get_random_bytes(16)
        iv = get_random_bytes(16)
        key = PBKDF2(self.__secret, salt, dkLen=32)
        cipher = AES.new(key, AES.MODE_CFB, iv=iv)
        return base64.b64encode(salt + iv + cipher.encrypt(plain.encode())).decode()
    
    def __decrypt(self, encoded: str | None):
        if not encoded:
            return encoded
        encrypted_data = base64.b64decode(encoded)
        salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        key = PBKDF2(self.__secret, salt, dkLen=32)
        cipher = AES.new(key, AES.MODE_CFB, iv=iv)
        return cipher.decrypt(ciphertext).decode()

    @staticmethod
    def __export_manual_mode(data: OperationMode | None):
        return None if (data is None) else data.value

    @staticmethod
    def __export_schedule(data: dict[datetime, OperationMode]):
        return {x.isoformat(): y.value for x, y in data.items()}

    @staticmethod
    def __export_template(data: Iterable[OperationMode]):
        return list(x.value for x in data)

    @staticmethod
    def __import_manual_mode(data: str):
        return None if (not data) else OperationMode.get(data)

    @staticmethod
    def __import_schedule(data: dict):
        return {datetime.fromisoformat(x): OperationMode.get(y) for x, y in (data.get(_SCHEDULE_DATA_KEY) or {}).items()}

    @staticmethod
    def __import_template(data: list):
        return tuple(OperationMode.get(x) for x in data)

    @staticmethod
    def __get_schedule_template_index(timestamp: datetime):
        minutes_since_midnight = int((timestamp - timestamp.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()) // 60
        return minutes_since_midnight // 15

app_state = AppState()