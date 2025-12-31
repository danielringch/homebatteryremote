from ..uplink import VirtualController
from ..price import PriceSource

class Singletons:
    def __init__(self):
        self.__price: PriceSource = None
        self.__virtual_controller: VirtualController = None
    
    @property
    def price(self):
        return self.__price
    
    @property
    def virtual_controller(self):
        return self.__virtual_controller
    
    def set(self, controller: VirtualController, price: PriceSource):
        self.__price = price
        self.__virtual_controller = controller

singletons = Singletons()
