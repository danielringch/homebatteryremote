import argparse, yaml, logging, os
from modules.core import setup_log, app_state, get_config_key, triggers, password_hasher
from modules.energy import EnergyTracker, CapacityTracker
from modules.price import PriceSource
from modules.schedule import Scheduler
from modules.uplink import Mqtt, VirtualController

__version__ = "0.1.0"

_DATA_DIR_CONFIG_KEY = 'data_dir'
_SECRET_CONFIG_KEY = 'secret'

_DATA_DIR_ENV_NAME = 'HBRE_DATA_DIR'
_SECRET_ENV_NAME = 'HBRE_SECRET'

def main():
    parser = argparse.ArgumentParser(description='Remote control and energy tracking / trading software for the homebattery controller.')
    parser.add_argument('-c', '--config', type=str, required=True, help="Path to config file.")
    args = parser.parse_args()

    with open(args.config, "r") as stream:
        config = yaml.safe_load(stream)

    setup_log(config)

    secret = get_config_key(config, str, _SECRET_ENV_NAME, _SECRET_CONFIG_KEY)

    data_path = get_config_key(config, str, _DATA_DIR_ENV_NAME, _DATA_DIR_CONFIG_KEY)
    data_file = os.path.join(data_path, 'homebattery_remote_instance_data.json')
    app_state.load_config(secret, config)
    app_state.load_file(data_file)
    app_state.start()

    logging.debug(f'homebattery remote {__version__}; instance: {app_state.data.instance_name.value}')

    mqtt = Mqtt(config)
    virtual_controller = VirtualController(config, mqtt)
    prices = PriceSource()
    scheduler = Scheduler(virtual_controller)
    capacity_tracker = CapacityTracker(virtual_controller, prices)
    energy_tracker = EnergyTracker(config, virtual_controller, prices)

    # nicegui reads some environment variables on import, so we need to delay related imports until all data is available
    os.environ['MATPLOTLIB'] = 'false'
    os.environ['NICEGUI_STORAGE_PATH'] = os.path.join(data_path, 'sessions')
    from modules.gui import singletons, Gui

    singletons.set(virtual_controller, prices)
    gui = Gui(config)

    def start():
        mqtt.start()
        scheduler.start()
        prices.start()
        triggers.start()
    gui.run(
        storage_secret=password_hasher.hash(password=secret, salt='8J3pZzuzph6nibo2'.encode()).split('$')[-1],
        startup_callback=start)

if __name__ == "__main__":
    main()
