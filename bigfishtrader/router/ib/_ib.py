# encoding:utf-8
import logging
from ib.ext import EWrapper
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.opt import ibConnection, message
from bigfishtrader.router.ib.constants import *


class BFIbApi(object):
    def __init__(self, logger=""):
        self.conn = ibConnection(port=4001, clientId=123)
        # self.conn.register(self.on_update_account_value, "UpdateAccountValue")
        self.conn.register(self.on_tick, message.tickSize, message.tickPrice, message.tickString)
        self.conn.register(self.on_current_time, "CurrentTime")
        self.conn.register(self.on_order_status, message.orderStatus)
        self.conn.register(self.on_open_order, message.openOrder)
        self.conn.register(self.on_exec_details, message.execDetails)
        self.conn.register(self.on_next_valid_identity, message.nextValidId)
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
        print(msg)

    def on_open_order(self, msg):
        print(msg.contract)
        print(msg.order)
        print(msg.orderState)

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

    print(message.orderStatus)
    print(message.openOrder)
    print(message.execDetails)
    api = BFIbApi()
    api.conn.connect()
    time.sleep(4)
    api.conn.reqCurrentTime()
    contract_tuple = ('EUR', 'CASH', 'IDEALPRO', 'USD', '233', 0.0, '')
    symbol = make_stk_contract(contract_tuple)
    api.symbol = symbol
    # api.conn.reqMktData(1, symbol, "", False)

    api.send_order(api.symbol, 20000)
    # time.sleep(1)
    api.send_order(api.symbol, -20000)
    while True:
        time.sleep(1)
