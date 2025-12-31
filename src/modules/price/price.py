from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from ..core import app_state
from .tibber import Tibber

@dataclass
class Prices:
    charge: Decimal
    discharge: Decimal

class PriceSource:
    def __init__(self):
        self.__tibber = Tibber()

        self.__efficiency_factor = Decimal(1)
        self.__get_efficiency_factor()

        app_state.data.charger_efficiency.on_change.subscribe(self.__get_efficiency_factor)
        app_state.data.inverter_efficiency.on_change.subscribe(self.__get_efficiency_factor)

    def start(self):
        self.__tibber.start()

    def get_at(self, timestamp):
        if (not self.__tibber.is_active) or (not (price := self.__tibber.get_price(timestamp))):
            return None

        charge_price = round(price / self.__efficiency_factor, 4)
        return Prices(charge=charge_price, discharge=price)
    
    def get_previous(self):
        # Shortly after quarter change, the correct price would still be the one from the previous quarter.
        # So a bit of time needs to be substracted to get the price from the correct quarter.
        return self.get_at((datetime.now() - timedelta(minutes=2)))
    
    def __get_efficiency_factor(self, _ = None):
        self.__efficiency_factor = app_state.data.charger_efficiency.value * app_state.data.inverter_efficiency.value
