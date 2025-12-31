from datetime import datetime
from decimal import Decimal
from statistics import mean

from ...core import OperationMode, app_state, SCHEDULE_LENGTH
from ..singletons import singletons
from .modeltypes import BindableValue, BridgedValue

_DATE_FORMAT_DMY_HM = "%d.%m.%y %H:%M"

class ScheduleRow:
    def __init__(self):
        self.raw_timestamp = datetime.min
        self.timestamp = BindableValue('')
        self.mode = BindableValue('')
        self.color = BindableValue('')
        self.charge_price = BindableValue('')
        self.discharge_price = BindableValue('')
        self.charge_margin = BindableValue('')
        self.battery_margin = BindableValue('')

class ScheduleModel:
    def __init__(self, id: str):
        self.__id = id

        self.is_dirty = BindableValue(False)

        self.capacity = BridgedValue(id, app_state.data.remaining_capacity, self.__print_capacity)
        self.avg_price = BridgedValue(id, app_state.data.avg_charged_price, self.__print_avg_price)

        self.schedule = [ScheduleRow() for _ in range(SCHEDULE_LENGTH)]

        app_state.data.avg_charged_price.on_change.subscribe(self.refresh, id=id)
        app_state.data.minimum_margin.on_change.subscribe(self.refresh, id=id)
        app_state.data.charger_efficiency.on_change.subscribe(self.refresh, id=id)
        app_state.data.inverter_efficiency.on_change.subscribe(self.refresh, id=id)
        app_state.data.prices_revision.on_change.subscribe(self.refresh, id=id)
        app_state.data.schedule.on_change.subscribe(self.refresh, id=id)
        self.refresh()

    def destroy(self):
        self.capacity.destroy()
        self.avg_price.destroy()
        app_state.data.avg_charged_price.on_change.unsubscribe_by_id(self.__id)
        app_state.data.minimum_margin.on_change.unsubscribe_by_id(self.__id)
        app_state.data.charger_efficiency.on_change.unsubscribe_by_id(self.__id)
        app_state.data.inverter_efficiency.on_change.unsubscribe_by_id(self.__id)
        app_state.data.prices_revision.on_change.unsubscribe_by_id(self.__id)
        app_state.data.schedule.on_change.unsubscribe_by_id(self.__id)

    def refresh(self, _ = None):
        if self.is_dirty.value:
            # changes to capacity and avg price happen quite often,
            # we want the user not loose their input
            return

        price_source = singletons.price
        schedule: dict[datetime, OperationMode] = app_state.data.schedule.value
        assert len(schedule) == SCHEDULE_LENGTH
        min_margin: Decimal = app_state.data.minimum_margin.value
        avg_charged_price: Decimal = app_state.data.avg_charged_price.value

        prices = {ts: prices for ts in schedule.keys() if (prices := price_source.get_at(ts))}
        
        price_values = prices.values()
        charge_minimum = min((x.charge for x in price_values), default=Decimal(0))
        charge_maximum = max((x.charge for x in price_values), default=Decimal(0))
        charge_avg = mean(x.charge for x in price_values) if price_values else Decimal(0)
        discharge_maximum = max((x.discharge for x in price_values), default=Decimal(0))

        previous_mode = None

        for i, timestamp in enumerate(sorted(schedule.keys())):
            row = self.schedule[i]
            row.raw_timestamp = timestamp
            row.timestamp.set(timestamp.strftime(_DATE_FORMAT_DMY_HM))
            mode = schedule[timestamp].value
            row.mode.set(None if (mode == previous_mode) else mode)
            previous_mode = mode  

            if (prices_at := prices.get(timestamp)):
                row.color.set(self.__get__color(charge_avg, charge_minimum, charge_maximum, prices_at.charge))

                row.charge_price.set(f'{(prices_at.charge * Decimal(100)):.2f}')

                row.discharge_price.set(f'{(prices_at.discharge * Decimal(100)):.2f}')

                if (battery_margin := (prices_at.discharge - avg_charged_price)) >= min_margin:
                    row.battery_margin.set(f'{(battery_margin * 100):.2f}')
                else:
                    row.battery_margin.set('')

                if (discharge_margin := (prices_at.discharge - charge_minimum)) >= min_margin:
                    row.charge_margin.set(f'{(discharge_margin * 100):.2f}')
                elif (discharge_maximum - prices_at.charge) >= min_margin:
                    charge_penalty = charge_minimum - prices_at.charge
                    row.charge_margin.set(f'{(charge_penalty * 100):.2f}')
                else:
                    row.charge_margin.set('')
            else:
                row.color.set("#A0A0A0")
                row.charge_price.set('')
                row.discharge_price.set('')
                row.charge_margin.set('')
                row.battery_margin.set('')

    def write_schedule(self):
        schedule: dict[datetime, OperationMode] = {}

        previous_mode = None
        for row in sorted(self.schedule, key=lambda x: x.raw_timestamp):
            timestamp = row.raw_timestamp
            mode = OperationMode(row.mode.value or previous_mode or OperationMode.IDLE.value)
            previous_mode = mode.value
            schedule[timestamp] = mode

        app_state.data.schedule.set(schedule)
        app_state.save()
        self.is_dirty.set(False)
        # a manual refresh call sanitizes the toggles
        self.refresh()

    @staticmethod
    def __print_capacity(capacity: Decimal | None):
        return f'{capacity:.1f} Ah' if (capacity >= 0) else '(unknown) Ah'
    
    @staticmethod
    def __print_avg_price(price: Decimal | None):
        return f'{(price * Decimal(100)):.2f} ct/kWh' if (price is not None) else '(unknown) ct/kWh'
    
    @staticmethod
    def __get__color(avg_val, min_val, max_val, value):
        value = min(max_val, max(min_val, value))
        if value > avg_val:
            norm_base = max_val - avg_val
            norm_value = value - avg_val
        else:
            norm_base = avg_val - min_val
            norm_value = norm_base - (value - min_val)
        other_channel = 255 - round(255 * norm_value / norm_base)
        other_hex = hex(other_channel)[2:].upper()
        other_hex = f'0{other_hex}' if len(other_hex) < 2 else other_hex
        if value > avg_val:
            return f'#FF{other_hex}{other_hex}'
        else:
            return f'#{other_hex}FF{other_hex}'
    