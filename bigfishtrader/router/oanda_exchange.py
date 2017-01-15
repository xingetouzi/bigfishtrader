import oandapy
import json
from bigfishtrader.quotation.base import AbstractPriceHandler
from bigfishtrader.router.base import AbstractRouter


class OandaExchange(AbstractRouter):
    def __init__(self, oanda_api, event_queue, **ticker_info):
        super(OandaExchange, self).__init__()
        self.api = oanda_api

    def on_cancel(self, event, kwargs=None):
        pass

    def on_bar(self, bar_event, kwargs=None):
        pass

    def on_order(self, event, kwargs=None):
        pass

    def get_orders(self):
        pass



if __name__ == '__main__':
    account_info = json.load(open('oanda_account.json'))
    api = oandapy.API(access_token=account_info['access_token'])
    # response = api.create_order(
    #     account_info['login'],
    #     instrument="EUR_USD",
    #     units=100,
    #     side='buy',
    #     type='market',
    # )

    response = api.get_trades(account_info['login'])
    print(response)
