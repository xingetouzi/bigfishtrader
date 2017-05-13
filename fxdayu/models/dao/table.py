from sqlalchemy import Table, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper

from fxdayu.models.data import AccountData, PositionData, ExecutionData
from fxdayu.models.order import OrderStatusData, OrderReq

Base = declarative_base()

account = Table(
    "account", Base.metadata,
    Column("gateway", String(10), primary_key=True),
    Column("accountID", String(20), primary_key=True),
    Column("preBalance", Float),
    Column("balance", Float),
    Column("available", Float),
    Column("commission", Float),
    Column("margin", Float),
    Column("closePnl", Float),
    Column("positionPnl", Float),
    Column("exchangeRate", Float)
)

position = Table(
    "position", Base.metadata,
    Column("gateway", String(10), primary_key=True),
    Column("account", String(20), primary_key=True),
    Column("symbol", String(10), primary_key=True),
    Column("sid", Integer),
    Column("exchange", String(10)),
    Column("side", String()),
    Column("volume", Integer),
    Column("frozenVolume", Integer),
    Column("avgPrice", Float),
    Column("marketValue", Float)
)

execution = Table(
    "execution", Base.metadata,
    Column("gateway", String(10), primary_key=True),
    Column("account", String(20), primary_key=True),
    Column("clOrdID", String(10), primary_key=True),

    Column("exchange", String(10)),
    Column("clientID", String(10)),
    Column("orderID", String(10)),
    Column("execID", String(10)),
    Column("time", DateTime),

    Column("symbol", String(10)),
    Column("action", String(5)),
    Column("side", String(5)),
    Column("profit", Float),

    Column("cumQty", Integer),
    Column("leavesQty", Integer),
    Column("lastQty", Integer),
    Column("avgPx", Float),
    Column("lastPx", Float),
)

order_status = Table(
    "order_status", Base.metadata,
    Column("gateway", String(10), primary_key=True),
    Column("account", String(20), primary_key=True),
    Column("clOrdID", String(10), primary_key=True),
    Column("secondaryClOrdID", String(10)),
    Column("exchange", String(10)),

    Column("side", String(5)),
    Column("action", String(5)),
    Column("symbol", String(10)),
    Column("price", Float),
    Column("orderQty", Integer),
    Column("cumQty", Integer),
    Column("leavesQty", Integer),
    Column("ordStatus", String(8)),
    Column("orderTime", DateTime),
    Column("cancelTime", DateTime),

)

order = Table(
    "order", Base.metadata,
    Column("gateway", String(10), primary_key=True),
    Column("account", String(20), primary_key=True),
    Column("clOrdID", String(10), primary_key=True),
    Column("exchange", String(10)),

    Column("symbol", String(10)),
    Column("side", String(5)),
    Column("action", String(5)),
    Column("orderQty", Integer),
    Column("ordType", String(8)),
    Column("price", Float),
    Column("stopPx", Float),
    Column("timeInForce", String(10)),
    Column("transactTime", DateTime),
    Column("expireTime", String(10)),
)

mapper(AccountData, account)
mapper(PositionData, position)
mapper(ExecutionData, execution)
mapper(OrderStatusData, order_status)
mapper(OrderReq, order)
