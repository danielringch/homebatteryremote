import csv, os, datetime, logging
from decimal import Decimal
from ..core import get_optional_config_key, ENERGY_CONFIG_KEY, EventPayload
from ..core.triggers import triggers
from ..uplink.virtualcontroller import VirtualController
from ..price import PriceSource

_CSV_FILE_CONFIG_KEY = 'csv_file'

class EnergyTracker:
    def __init__(self, config : dict, uplink: VirtualController, prices: PriceSource):
        self.__csv_file = get_optional_config_key(config, str, None, None, ENERGY_CONFIG_KEY, _CSV_FILE_CONFIG_KEY)
        if not self.__csv_file:
            return

        self.__prices = prices

        self.__solar_energy = 0
        self.__charger_energy = 0
        self.__inverter_energy = 0

        uplink.on_charger_energy.subscribe(self.__on_charger_energy)
        uplink.on_inverter_energy.subscribe(self.__on_inverter_energy)
        uplink.on_solar_energy.subscribe(self.__on_solar_energy)

        triggers.add('energy', '1/15 * * * *', self.__handle_energy)

    def __on_charger_energy(self, args: EventPayload[int]):
        self.__charger_energy += args.data

    def __on_inverter_energy(self, args: EventPayload[int]):
        self.__inverter_energy += args.data

    def __on_solar_energy(self, args: EventPayload[int]):
        self.__solar_energy += args.data

    def __handle_energy(self):
        now = datetime.datetime.now()
        price = self.__prices.get_previous()
        if price is None:
            logging.warning(f'Can not write energy statistics to file: no price data.')
            return
        cost = (price.discharge * Decimal(self.__charger_energy)) / Decimal(-1000)
        revenue = (price.discharge * Decimal(self.__inverter_energy)) / Decimal(1000)

        logging.debug(f'Energy from charger: {self.__charger_energy} Wh, cost={cost:.8f} €')
        logging.debug(f'Energy from inverter: {self.__inverter_energy} Wh, revenue={abs(revenue):.8f} €.')
        logging.debug(f'Energy from solar: {self.__solar_energy} Wh')

        if self.__charger_energy or self.__inverter_energy or self.__solar_energy:
            self.__write_to_csv(now, self.__charger_energy, self.__inverter_energy, self.__solar_energy, cost, revenue)
        self.__charger_energy = 0
        self.__inverter_energy = 0
        self.__solar_energy = 0

    def __write_to_csv(self, timestamp: datetime.datetime, charger_energy: int, inverter_energy: int, solar_energy: int, cost: Decimal, revenue:Decimal):
        assert self.__csv_file is not None
        file_exists = os.path.exists(self.__csv_file)
        with open(self.__csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(("timestamp", "charger energy", "inverter energy", "solar energy", "cost", "revenue"))
            timestamp = timestamp.replace(second=0, microsecond=0)
            writer.writerow((timestamp, charger_energy, inverter_energy, solar_energy, f'{cost:.8f}', f'{revenue:.8f}'))
