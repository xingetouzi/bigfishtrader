# encoding: utf-8
from __future__ import unicode_literals
from enum import Enum

EMPTY_STRING = b''
EMPTY_UNICODE = ""
EMPTY_INT = 0
EMPTY_FLOAT = 0.0


class ORDERTYPE(Enum):
    MARKET = "市价"
    LIMIT = "限价"
    STOP = "止损"
    FAK = "FAK"
    FOK = "FOK"


class ORDERSTATUS(Enum):
    UNFILL = 0
    FILL = 1


class DIRECTION(Enum):
    LONG = "多头"
    SHORT = "空头"


class ACTION(Enum):
    IN = "开"
    OUT = "平"
