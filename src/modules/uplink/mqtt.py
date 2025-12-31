import logging
import paho.mqtt.client as mqtt
from ssl import CERT_NONE

from ..core import get_config_key, get_optional_config_key

_MQTT_CONFIG_KEY = 'mqtt'
_HOST_CONFIG_KEY = 'host'
_CA_CONFIG_KEY = 'ca'
_TLS_INSECURE_CONFIG_KEY = 'tls_insecure'
_USER_CONFIG_KEY = 'user'
_PASSWORD_CONFIG_KEY = 'password'

_HOST_ENV_NAME = 'HBRE_MQTT_HOST'
_USER_ENV_NAME = 'HBRE_MQTT_USER'
_PASS_ENV_NAME = 'HBRE_MQTT_PASS'

class Mqtt():
    def __init__(self, config: dict):
        self.__mqtt = mqtt.Client()
        self.__mqtt.on_connect = self.__on_mqtt_connect
        self.__mqtt.on_message = self.__on_message

        self.__host, self.__port = get_config_key(config, lambda x: str(x).split(':'), _HOST_ENV_NAME, _MQTT_CONFIG_KEY, _HOST_CONFIG_KEY)

        ca_path = get_optional_config_key(config, str, None, None, _MQTT_CONFIG_KEY, _CA_CONFIG_KEY)
        is_tls_insecure = get_optional_config_key(config, bool, False, None, _MQTT_CONFIG_KEY, _TLS_INSECURE_CONFIG_KEY)
        if ca_path or is_tls_insecure:
            self.__mqtt.tls_set(ca_certs=ca_path, cert_reqs=CERT_NONE if is_tls_insecure else None)

        user = get_optional_config_key(config, str, None, _USER_ENV_NAME, _MQTT_CONFIG_KEY, _USER_CONFIG_KEY)
        password = get_optional_config_key(config, str, None, _PASS_ENV_NAME, _MQTT_CONFIG_KEY, _PASSWORD_CONFIG_KEY)
        if user or password:
            self.__mqtt.username_pw_set(user, password)

        self.__subscriptions = {}

    def __del__(self):
        self.__mqtt.loop_stop()

    def start(self):
        self.__mqtt.connect(self.__host, int(self.__port), 60)
        self.__mqtt.loop_start()

    def subscribe(self, topic, qos, callback):
        assert topic not in self.__subscriptions
        self.__subscriptions[topic] = qos
        self.__mqtt.message_callback_add(topic, lambda client, userdata, msg: callback(msg))

    def publish(self, topic: str, payload, qos: int, retain=False):
        self.__mqtt.publish(topic, payload, qos=qos, retain=retain)

    def __on_mqtt_connect(self, client, userdata, flags, rc):
        logging.debug(f'MQTT connected with code {rc}.')
        for topic, qos in self.__subscriptions.items():
            self.__mqtt.subscribe(topic, qos=qos)

    def __on_message(self, client, userdata, msg):
        logging.error(f'Unknown MQTT message at topic {msg.topic}: {msg.payload}.')

