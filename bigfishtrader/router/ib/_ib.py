# encoding:utf-8
import logging
from ib.ext.Contract import Contract
from ib.opt import ibConnection, message


class BFIbApi(object):
    def __init__(self, logger=""):
        self.conn = ibConnection(port=7497, clientId=123)
        self.conn.register(self.on_update_account_value, "UpdateAccountValue")
        print(message.tickString)
        self.conn.register(self.on_tick, message.tickSize, message.tickPrice, message.tickString)
        self.conn.register(self.on_current_time, "CurrentTime")
        self._logger = logging.getLogger(logger)
        self._symbol = None

    @property
    def symbol(self):
        return "%s_%s" % (self._symbol.m_symbol, self._symbol.m_currency)

    @symbol.setter
    def symbol(self, contract):
        if not isinstance(symbol, Contract):
            return
        self._symbol = contract

    def on_update_account_value(self, msg):
        pass

    def on_current_time(self, msg):
        self._logger.info(msg.time)

    def on_tick(self, msg):
        self._logger.info(str(msg))
        if msg.field == 1:
            print ('%s: bid: %s' % (self.symbol, msg.price))
        elif msg.field == 2:
            print ('%s: ask: %s' % (self.symbol, msg.price))


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
    api = BFIbApi()
    api.conn.connect()
    api.conn.reqCurrentTime()
    contract_tuple = ('EUR', 'CASH', 'IDEALPRO', 'USD', '', 0.0, '')
    symbol = make_stk_contract(contract_tuple)
    api.symbol = symbol
    api.conn.reqMktData(1, symbol, "", False)
    raw_input()
