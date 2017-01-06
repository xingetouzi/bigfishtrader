from enum import Enum

__all__ = ["ORDER_STATUS"]


class ORDER_STATUS(Enum):
    UNFILL = 0
    FILL = 1
