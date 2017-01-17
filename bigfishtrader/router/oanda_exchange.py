import oandapy
import json
from bigfishtrader.event import EVENTS
from bigfishtrader.router.base import AbstractRouter
from bigfishtrader.engine.handler import Handler


class OandaExchange(AbstractRouter):
    def __init__(self, oanda_api, event_queue, trade_type='paper', **ticker_info):
        super(OandaExchange, self).__init__()
        self.api = oanda_api
        self._handlers = {
            "on_bar": Handler(self.on_bar, EVENTS.BAR, topic="", priority=100),
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic=".", priority=0)
        }

    def on_cancel(self, event, kwargs=None):
        pass

    def on_bar(self, bar_event, kwargs=None):
        pass

    def on_order(self, event, kwargs=None):
        pass

    def get_orders(self):
        pass



if __name__ == '__main__':
    import requests
    account_info = json.load(open('D:/bigfishtrader/oanda_account.json'))
    api = oandapy.API(access_token=str(account_info['access_token']))
    # response = api.create_order(
    #     account_info['login'],
    #     instrument="EUR_USD",
    #     units=100,
    #     side='buy',
    #     type='market',
    # )



    response = api.get_trades(account_info['login'])
    print(response)
