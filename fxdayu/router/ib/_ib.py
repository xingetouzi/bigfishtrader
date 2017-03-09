# encoding:utf-8
import logging
from datetime import datetime
from weakref import proxy
from copy import copy

from dateutil.parser import parse
import numpy as np
from ib.ext.Contract import Contract
from ib.ext.Order import Order
import ib.ext.Execution
from ib.opt import ibConnection, message
from fxdayu.router.gateway import Gateway
from fxdayu.router.ib.constants import *
from fxdayu.event import TickEvent, ExecutionEvent
from fxdayu.model import ExecutionData


class BFWrapper(object):
    def __init__(self, gateway):
        """

        Args:
            gateway: fxdayu.router.gateway

        Returns:

        """
        self.connection = ibConnection(port=4001, clientId=123)
        self.gateway = proxy(gateway)
        self._next_order_id = 0
        self._ticks = {}
        self._tick_completed = set()
        self._symbols = {}
        self.connection.register(self.updateMktDepth, message.updateMktDepth)
        self.connection.register(self.execDetails, message.execDetails)
        self.connection.register(self.nextValidId, message.nextValidId)

    @property
    def next_order_id(self):
        result = self._next_order_id
        self._next_order_id += 1
        return result

    def on_tick(self, tick):
        if tick.ticker not in self._tick_completed:
            if np.isnan(tick.ask_price).sum() + np.isnan(tick.bid_price).sum() <= tick.depth - 2:
                return
            else:
                self._tick_completed.add(tick.ticker)
        event = copy(tick)
        event.time = datetime.now()
        self.gateway.on_tick(event)

    def connect(self):
        return self.connection.connect()

    def disconnect(self):
        return self.connection.disconnect()

    def updateMktDepth(self, msg):
        if msg.tickerId not in self._ticks:
            self._ticks[msg.tickerId] = TickEvent()
            self._ticks[msg.tickerId].ticker = msg.tickerId
        tick = self._ticks[msg.tickerId]
        if msg.operation == 2:
            p = np.nan
            v = np.nan
        else:
            p = msg.price
            v = msg.size
        if msg.side == 0:
            tick.ask_price[msg.position] = p
            tick.ask_volume[msg.position] = v
        else:
            tick.bid_price[msg.position] = p
            tick.bid_volume[msg.position] = v
        self.on_tick(tick)

    def updateMktDepthL2(self, tickerId, position, marketMaker, operation, side, price, size):
        pass

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId,
                    lastFillPrice, clientId, whyHeld):
        pass

    def openOrder(self, orderId, contract, order, orderState):
        pass

    def execDetails(self, msg):
        reqId = msg.reqId
        contract = msg.contract
        execution = msg.execution
        fill = ExecutionData()
        fill.time = parse(execution.m_time)
        fill.ticker = contract
        fill.action = execution.m_side
        fill.quantity = execution.m_shares
        fill.price = execution.m_price
        fill.exchange = execution.m_exchange
        fill.order_ext_id = execution.m_permId
        fill.avg_price = execution.m_avgPrice
        fill.account = execution.m_acctNumber
        event = ExecutionEvent(
            fill,
            timestamp=execution.m_time
        )
        self.gateway.event_engine.event_queue.put(event)

    def nextValidId(self, msg):
        self._next_order_id = max(self._next_order_id, msg.orderId)


class IbGateway(Gateway):
    def __init__(self, eventEngine, gatewayName):
        super(IbGateway, self).__init__(eventEngine, gatewayName)
        self.ib_wrapper = BFWrapper(self)

    @staticmethod
    def create_order(quantity, is_buy, is_market_order=True):
        order = Order()
        order.m_totalQuantity = quantity
        order.m_orderType = ORDER_TYPE_MARKET if is_market_order else ORDER_TYPE_LIMIT
        order.m_action = ORDER_ACTION_BUY if is_buy else ORDER_ACTION_SELL
        return order

    @staticmethod
    def make_contract(ticker):
        new_contract = Contract()
        ct = ('EUR', 'CASH', 'IDEALPRO', 'USD', '', 0.0, '')
        new_contract.m_symbol = ct[0]
        new_contract.m_secType = ct[1]
        new_contract.m_exchange = ct[2]
        new_contract.m_currency = ct[3]
        new_contract.m_expiry = ct[4]
        new_contract.m_strike = ct[5]
        new_contract.m_right = ct[6]
        return new_contract

    def send_order(self, event, kwargs=None):
        print(event.action)
        qty = event.quantity
        order = self.create_order(abs(qty), is_buy=event.action)
        contract = self.make_contract(event.ticker)
        self.ib_wrapper.connection.placeOrder(self.ib_wrapper.next_order_id, contract, order)

    def subscribe(self, ticker):
        self.ib_wrapper.connection.reqMktDepth(2001, self.make_contract(ticker), 10)


class BFIbApi(object):
    def __init__(self, logger=""):
        self.conn = ibConnection(port=4001, clientId=123456)
        self._symbols = {}
        # self.conn.register(self.on_update_account_value, "UpdateAccountValue")
        self.conn.register(self.on_tick, message.tickSize, message.tickPrice, message.tickString, message.tickEFP,
                           message.tickGeneric)
        self.conn.register(self.on_current_time, "CurrentTime")
        # self.conn.register(self.on_order_status, message.orderStatus)
        # self.conn.register(self.on_open_order, message.openOrder)
        self.conn.register(self.on_exec_details, message.execDetails)
        self.conn.register(self.on_next_valid_identity, message.nextValidId)
        self.conn.register(self.on_depth, message.updateMktDepth)
        self._logger = logging.getLogger(logger)
        self._symbol = None
        self._order_id = 0

    @property
    def symbol_str(self):
        return "%s_%s" % (self._symbol.m_symbol, self._symbol.m_currency)

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, contract):
        if not isinstance(symbol, Contract):
            return
        self._symbol = contract

    def on_update_account_value(self, msg):
        print(msg)

    def on_current_time(self, msg):
        self._logger.info(msg.time)

    def on_tick(self, msg):
        self._logger.info(str(msg))
        if msg.field == 1:
            print ('%s: bid: %s' % (self.symbol_str, msg.price))
        elif msg.field == 2:
            print ('%s: ask: %s' % (self.symbol_str, msg.price))

    @staticmethod
    def create_order(quantity, is_buy, is_market_order=True):
        order = Order()
        order.m_totalQuantity = quantity
        order.m_orderType = ORDER_TYPE_MARKET if is_market_order else ORDER_TYPE_LIMIT
        order.m_action = ORDER_ACTION_BUY if is_buy else ORDER_ACTION_SELL
        return order

    def send_order(self, contract, qty):
        order = self.create_order(abs(qty), qty > 0)
        self.conn.placeOrder(self.next_order_id,
                             contract,
                             order)

    def on_next_valid_identity(self, msg):
        self._order_id = msg.orderId

    def on_order_status(self, msg):
        print(msg)

    def on_exec_details(self, msg):
        print(msg.contract)
        e = msg.execution
        print([e.m_orderId,
               e.m_clientId,
               e.m_execId,
               e.m_time,
               e.m_acctNumber,
               e.m_exchange,
               e.m_side,
               e.m_shares,
               e.m_price,
               e.m_permId,
               e.m_liquidation,
               e.m_cumQty,
               e.m_avgPrice,
               e.m_orderRef,
               e.m_evRule,
               e.m_evMultiplier])

    def on_open_order(self, msg):
        print(msg.contract)
        print(msg.order)
        print(msg.orderState)

    def on_depth(self, msg):
        print(msg)
        # self._logger.info(str(msg))

    @property
    def next_order_id(self):
        result = self._order_id
        self._order_id += 1
        return result


def make_stk_contract(ct):
    new_contract = Contract()
    new_contract.m_symbol = ct[0]
    new_contract.m_secType = ct[1]
    new_contract.m_exchange = ct[2]
    new_contract.m_currency = ct[3]
    new_contract.m_expiry = ct[4]
    new_contract.m_strike = ct[5]
    new_contract.m_right = ct[6]
    print ('Contract Values:%s,%s,%s,%s,%s,%s,%s:' % ct)
    return new_contract


if __name__ == "__main__":
    import time

    api = BFIbApi()
    api.conn.connect()
    api.conn.reqCurrentTime()
    contract_tuple = ('EUR', 'CASH', 'IDEALPRO', 'USD', '', 0.0, '')
    symbol = make_stk_contract(contract_tuple)
    api.symbol = symbol
    # api.conn.reqMktData(1, symbol, "", True)
    # api.conn.reqMktData(2, symbol, "", False)
    # api.conn.reqMktDepth(2001, symbol, 10)
    api.send_order(api.symbol, 20000)
    # time.sleep(1)
    api.send_order(api.symbol, -20000)
    while True:
        time.sleep(1)
        raw_input()
