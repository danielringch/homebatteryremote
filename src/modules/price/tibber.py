import aiohttp, asyncio, traceback, logging
from datetime import datetime as dt
from datetime import timedelta
from decimal import Decimal

from ..core import Triggers, app_state


_PRICE_REQUEST = {"query": "{ viewer { homes { currentSubscription{ priceInfo(resolution: QUARTER_HOURLY) { today { total startsAt } tomorrow { total startsAt }}}}}}"}

class Tibber:
    def __init__(self):
        self.__prices: dict[dt, Decimal] = {}
        self.__token = app_state.data.tibber_token.value
        self.__task = None

    @property
    def is_active(self):
        return bool(self.__token)
    
    def start(self):
        app_state.data.tibber_token.on_change.subscribe(self.__config_change_handler)
        self.__config_change_handler()

    def get_price(self, timestamp: dt) -> Decimal | None:
        timestamp = Triggers.truncate_timestamp(timestamp)
        return self.__prices.get(timestamp, None)
    
    async def __update(self):
        while True:
            try:
                now = Triggers.truncate_timestamp(dt.now())
                if now + timedelta(hours=11) not in self.__prices:
                    await self.__get_prices()
        
            except Exception as e:
                logging.error(f'Tibber price update failed: {e}\n{traceback.format_exc()}')
            await asyncio.sleep(20 * 60)
    
    async def __get_prices(self):
        async with aiohttp.ClientSession() as session:
            response_json = await self.__post(session, _PRICE_REQUEST)
            if response_json is None:
                return

        raw_price_data = response_json['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']
        prices_today = raw_price_data['today']
        prices_tomorrow = raw_price_data['tomorrow']
        last_hour = Triggers.truncate_timestamp(dt.now()) - timedelta(hours=1)
        updated_prices = 0
        for raw_price in prices_today + prices_tomorrow:
            start = Triggers.truncate_timestamp(dt.fromisoformat(raw_price['startsAt'])).replace(tzinfo=None)
            if start < last_hour:
                continue
            price = round(Decimal(raw_price['total']), 4)
            if start not in self.__prices:
                updated_prices += 1
                logging.debug(f'Price at {start}: {price:.4f} €')
            self.__prices[start] = price
                
        logging.debug(f'Loaded {updated_prices} new price entries.')
        if updated_prices:
            app_state.data.prices_revision.set(dt.now())

    async def __post(self, session, query):
        token = self.__token
        if not token:
            return None
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        async with session.post('https://api.tibber.com/v1-beta/gql', json=query, headers=headers) as response:
            response_json = await response.json()
            status = response.status
        if not (status >= 200 and status <= 299):
            logging.debug(f'Tibber price update failed with code {status}.')
            return None
        return response_json

    def __config_change_handler(self, _ = None):
        self.__token = app_state.data.tibber_token.value
        if self.__token:
            if self.__task is None:
                self.__task = asyncio.create_task(self.__update())
        else:
            self.__prices.clear()
            app_state.data.prices_revision.set(dt.now())
            if self.__task:
                self.__task.cancel()
                self.__task = None