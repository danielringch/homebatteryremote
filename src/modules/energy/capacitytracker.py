import logging
from decimal import Decimal
from ..core import app_state, EventPayload
from ..uplink.virtualcontroller import VirtualController
from ..price import PriceSource

class CapacityTracker:
    def __init__(self, uplink: VirtualController, prices: PriceSource):
        self.__prices = prices

        self.__solar_energy: int | None = None
        self.__charger_energy: int | None = None

        uplink.on_battery_capacity.subscribe(self.__on_battery_capacity)
        uplink.on_charger_energy.subscribe(self.__on_charger_energy)
        uplink.on_solar_energy.subscribe(self.__on_solar_energy)

    def __on_battery_capacity(self, args: EventPayload[Decimal]):
        capacity = args.data
        old_capacity = app_state.data.remaining_capacity.value

        if old_capacity < 0:
            app_state.data.remaining_capacity.set(capacity)
            logging.debug('Init battery capacity tracker.')
            return
        if (self.__charger_energy is None) or (self.__solar_energy is None):
            return
        
        app_state.data.remaining_capacity.set(capacity)
        delta = capacity - old_capacity

        charger_eta = app_state.data.charger_efficiency.value
        solar_energy = self.__solar_energy
        charger_energy = round(self.__charger_energy * charger_eta)
        self.__solar_energy = None
        self.__charger_energy = None

        if delta == 0:
            return
        logging.debug(f'New total capacity: {capacity:.1f} Ah; change: {delta:.1f} Ah')
        if delta < 0:
            return

        price = prices.charge if (prices := self.__prices.get_previous()) else None
        if price is None:
            logging.warning('Omit average charged price calculation: no price available.')
            return

        total_energy = solar_energy + charger_energy
        if total_energy <= 0:
            logging.warning('Omit average charged price calculation: unknown energy source.')
            return

        effective_price = price * Decimal(round(charger_energy / total_energy, 10))
        logging.debug(f'Charge price: {price:.4f} €/kWh; effective charge price with solar: {effective_price:.4f} €/kWh.')

        worth = (old_capacity * app_state.data.avg_charged_price.value) + (delta * effective_price)
        new_avg = round(worth / capacity, 10)
        logging.debug(f'New average charged price: {new_avg:.4f} €/kWh.')
        app_state.data.avg_charged_price.set(new_avg)
        app_state.save()

    def __on_charger_energy(self, args: EventPayload[int]):
        self.__charger_energy = (self.__charger_energy or 0) + args.data

    def __on_solar_energy(self, args: EventPayload[int]):
        self.__solar_energy = (self.__solar_energy or 0) + args.data
