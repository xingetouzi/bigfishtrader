# encoding:utf-8

import json
import logging
from datetime import datetime, timedelta

import pytz

from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import EVENTS, TickEvent, OPEN_ORDER, CLOSE_ORDER, FillEvent
from bigfishtrader.router.base import AbstractRouter
from bigfishtrader.router.oanda.vnoanda import OandaApi, FUNCTIONCODE_STREAMPRICES, FUNCTIONCODE_GETINSTRUMENTS


class OandaRouter(AbstractRouter):
    def __init__(self, oanda_api):
        """

        Args:
            oanda_api(BFOandaApi): oanda api

        Returns:

        """
        super(OandaRouter, self).__init__()
        self.api = oanda_api
        self._handlers = {
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic=".", priority=0)
        }

    def on_cancel(self, event, kwargs=None):
        pass

    def on_bar(self, bar_event, kwargs=None):
        pass

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.OrderEvent): OrderEvent
            kwargs:

        Returns:
            None
        """
        if event.action == OPEN_ORDER:
            # market order
            params = {
                "instrument": event.ticker,
                "units": abs(event.quantity),
                "side": "buy" if event.quantity > 0 else "sell",
            }
            if event.order_type == EVENTS.ORDER:
                params["type"] = "market"
            event.order_id = self.api.sendOrder(params)
        else:
            event.order_id = self.api.closeTrade(event.exchange_id)

    def get_orders(self):
        pass


class BFOandaApi(OandaApi):
    """
    inherit from vnoanda.OanApi

    Args:
        event_queue: event_queue to put event
        logger: logger name
    """
    def __init__(self, event_queue, logger=""):
        super(BFOandaApi, self).__init__()
        self.event_queue = event_queue
        self._logger = logging.getLogger(logger)
        self._symbols = None
        self._timedelta = timedelta(0)
        self._ema_factor = 1 / 5
        self.tz = pytz.timezone("Asia/Shanghai")

    def _get_datetime(self, string):
        return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc).astimezone(tz=self.tz)

    def init(self, settingName, token, accountId, symbols=None):
        self._symbols = symbols
        super(BFOandaApi, self).init(settingName, token, accountId)

    def set_symbols(self, symbols):
        self._symbols = symbols

    def onPrice(self, data):
        if "tick" in data:
            ticker = data["tick"]
            self.event_queue.put(
                TickEvent(
                    ticker['instrument'],
                    self._get_datetime(ticker["time"]),
                    ticker['ask'], ticker['bid']
                )
            )
            # elif "heartbeat" in data:
            #     local_t = self.tz.localize(datetime.now())
            #     hb = data["heartbeat"]
            #     delta_t = local_t - datetime.strptime(hb['time'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(
            #         tzinfo=pytz.utc).astimezone(tz=self.tz)
            #     self._timedelta = self._ema_factor * delta_t + (1 - self._ema_factor) * self._timedelta
            #     print(self._timedelta)

    def onSendOrder(self, data, reqID):
        """
        callback of SendOrder's response
        response examples: ::

            {
                u'price': 1.06345,
                u'tradeReduced': {

                },
                u'instrument': u'EUR_USD',
                u'tradesClosed': [

                ],
                u'time': u'2017-01-19T18: 52: 55.000000Z',
                u'tradeOpened': {
                    u'stopLoss': 0,
                    u'takeProfit': 0,
                    u'side': u'buy',
                    u'trailingStop': 0,
                    u'units': 1000,
                    u'id': 10610751977L
                }
            }

        Args:
            data(dct): response body
            reqID(int): request identity
        Returns:
            None
        """
        print("PLACED")
        print(data, reqID)
        self._logger.info("Order <Ref: %s, ID: %s> has been placed at %s" % (
            reqID, data["tradeOpened"]["id"], self._get_datetime(data["time"]).isoformat()))

    def onCloseTrade(self, data, reqID):
        """
        callback of CloseTrade's response
        response examples: ::

            {
                u'profit': 0.38,
                u'price': 1.06274,
                u'side': u'buy',
                u'instrument': u'EUR_USD',
                u'time': u'2017-01-19T18: 39: 00.000000Z',
                u'id': 10610744365L
            }

        Args:
            data(dct): response body
            reqID: response id

        Returns:
            None
        """
        print("PLACED")
        print(data, reqID)
        self._logger.info(
            "Order <Ref: %s, ID: %s> has been placed at %s" % (
                reqID, data["id"], self._get_datetime(data["time"]).isoformat()))

    def onEvent(self, data):
        """
        callback of Oanda's event stream, handle data such as order status report,
        contains heartbeat
        response examples:
            + type: "TradeClose": ::

                {
                    u'transaction': {
                        u'tradeId': 10610704020L,
                        u'accountBalance': 100000.3793,
                        u'price': 1.06274,
                        u'side': u'sell',
                        u'instrument': u'EUR_USD',
                        u'interest': -0.0007,
                        u'time': u'2017-01-19T18: 39: 00.000000Z',
                        u'units': 1000,
                        u'type': u'TRADE_CLOSE',
                        u'id': 10610744365L,
                        u'pl': 0.38,
                        u'accountId': 7370328
                    }
                }

        Args:
            data(dct): response body

        Returns:
            None
        """
        if "transaction" in data:
            transaction = data["transaction"]
            if transaction["type"] == "MARKET_ORDER_CREATE":
                event = FillEvent(
                    self._get_datetime(transaction["time"]),
                    transaction["instrument"],
                    OPEN_ORDER,
                    transaction["units"] if transaction["side"] == "buy" else -transaction["units"],
                    transaction["price"],
                )
                event.exchange_id = str(transaction["id"])
                self.event_queue.put(event)
            elif transaction["type"] == "TRADE_CLOSE":
                event = FillEvent(
                    self._get_datetime(transaction["time"]),
                    transaction["instrument"],
                    CLOSE_ORDER,
                    transaction["units"] if transaction["side"] == "sell" else -transaction["units"],
                    transaction["price"]
                )
                event.exchange_id = str(transaction["id"])
                self.event_queue.put(event)
        elif "heartbeat" in data:
            heartbeat = data["heartbeat"]
            self._logger.info("Heartbeat at %s" % heartbeat["time"])

    def processStreamPrices(self):
        if self._symbols is None:
            # 首先获取所有合约的代码
            setting = self.functionSetting[FUNCTIONCODE_GETINSTRUMENTS]
            req = {'url': self.restDomain + setting['path'],
                   'method': setting['method'],
                   'params': {'accountId': self.accountId}}
            r, error = self.processRequest(req)
            if r:
                try:
                    data = r.json()
                    symbols = [d['instrument'] for d in data['instruments']]
                except Exception, e:
                    self.onError(e, -1)
                    return
            else:
                self.onError(error, -1)
                return
        else:
            symbols = self._symbols

        # 然后订阅所有的合约行情
        setting_ = self.functionSetting[FUNCTIONCODE_STREAMPRICES]
        params = {
            "accountId": self.accountId,
            "instruments": ",".join(symbols)
        }
        req = {'url': self.streamDomain + setting_['path'],
               'method': setting_['method'],
               'params': params,
               'stream': True}
        r, error = self.processRequest(req)

        if r:
            for line in r.iter_lines():
                if line:
                    try:
                        msg = json.loads(line)

                        if self.DEBUG:
                            print self.onPrice.__name__

                        self.onPrice(msg)
                    except Exception, e:
                        self.onError(e, -1)

                if not self.active:
                    break
        else:
            self.onError(error, -1)
