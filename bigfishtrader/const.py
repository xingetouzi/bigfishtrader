# encoding: utf-8
from enum import Enum

__all__ = ["ORDERSTATUS"]


class ORDERSTATUS(Enum):
    UNFILL = 0
    FILL = 1


class DIRECTION(Enum):
    LONG = u"多头"
    SHORT = u"空头"


class ACTION(Enum):
    IN = u"开"
    OUT = u"平"
