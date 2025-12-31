from enum import Enum

class OperationMode(Enum):
    IDLE = 'idle'
    CHARGE = 'charge'
    DISCHARGE = 'discharge'
    PROTECT = 'protect'

    @classmethod
    def get(cls, value):
        try:
            return cls(value)
        except:
            return cls('idle')
