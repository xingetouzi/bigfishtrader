# encoding:utf-8

import logging
import json
from datetime import datetime, timedelta

import pytz

from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import EVENTS, TickEvent, OPEN_ORDER, CLOSE_ORDER, FillEvent
from bigfishtrader.router.base import AbstractRouter
from bigfishtrader.vnoanda import OandaApi, FUNCTIONCODE_STREAMPRICES, FUNCTIONCODE_GETINSTRUMENTS


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
            event.local_id = self.api.sendOrder(params)
        else:
            event.local_id = self.api.closeTrade(event.exchange_id)

    def get_orders(self):
        pass


class BFOandaApi(OandaApi):
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
        print("PLACED")
        print(data, reqID)
        self._logger.info("Order <Ref: %s, ID: %s> has been placed at %s" % (
            reqID, data["tradeOpened"]["id"], self._get_datetime(data["time"]).isoformat()))

    def onCloseTrade(self, data, reqID):
        print("PLACED")
        print(data, reqID)
        self._logger.info(
            "Order <Ref: %s, ID: %s> has been placed at %s" % (
                reqID, data["id"], self._get_datetime(data["time"]).isoformat()))

    def onEvent(self, data):
        print("FILLED")
        print(data)
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
