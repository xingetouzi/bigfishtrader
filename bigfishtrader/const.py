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
    NOTTRADED = "未成交"
    PARTTRADED = "部分成交"
    ALLTRADED = "全部成交"
    CANCELLED = "已撤销"
    UNKNOWN = "未知"


class DIRECTION(Enum):
    NONE = "无方向"
    LONG = "多"
    SHORT = "空"
    UNKNOWN = "未知"


class ACTION(Enum):
    NONE = "无开平"
    OPEN = "开仓"
    CLOSE = "平仓"
    UNKNOWN = "未知"