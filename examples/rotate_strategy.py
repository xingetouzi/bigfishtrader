from bigfishtrader.strategy.base import Strategy


class RotateStrategy(Strategy):
    period = 10

    def initialize(self):
        self.set_commission(0.0005, 0.0005, 'value', 5)
        self.ticker = self.context.tickers[0]
        self.context.target = []
        self.time_limit(self.week_end, isoweekday=5, priority=101)

    def handle_data(self):
        for ticker, available in self.portfolio.security.items():
            if ticker not in self.context.target:
                if self.data.can_trade(ticker) and available:
                    self.portfolio.send_close(ticker=ticker, quantity=available)

        for ticker in self.context.target:
            if ticker not in self.portfolio.security.keys():
                if self.data.can_trade(ticker):
                    # self.open_position(ticker, 1000)
                    self.portfolio.send_open(ticker=ticker, quantity=1000)

    def week_end(self):
        target = {}
        for ticker in self.context.tickers:
            if not self.data.can_trade(ticker):
                continue

            close = self.data.history(ticker, 'D', length=self.period)['close']
            up = close[-1] / close.min()
            if len(target) < 2:
                target[ticker] = up
                continue

            for key, value in target.copy().items():
                if value > up:
                    target.pop(key)
                    target[ticker] = up
                    break

        self.context.target = list(target.keys())


if __name__ == '__main__':
    from bigfishtrader.trader import PracticeTrader
    from bigfishtrader.portfolio.portfolio import PositionPortfolio
    import pandas as pd
    from datetime import datetime

    # p = PracticeTrader().initialize(
    #     (
    #         'portfolio', PositionPortfolio,
    #         {'event_queue': 'event_queue', 'data': 'data', 'init_cash': 200000}
    #     ),
    #     data={'port': 27018, 'host': '192.168.0.103'}
    # ).backtest(
    #     RotateStrategy,
    #     ['000001', '600016', '600036', '600000', '601166'], 'D',
    #     start=datetime(2015, 1, 1), ticker_type='HS', period=15
    # )

    trader = PracticeTrader()

    o = trader.optimization(
        RotateStrategy,
        ['000001', '600016', '600036', '600000', '601166'], 'D',
        start=datetime(2015, 1, 1), ticker_type='HS',
        models=[(
            'portfolio', PositionPortfolio,
            {'event_queue': 'event_queue', 'data': 'data', 'init_cash': 200000}
        )],
        settings={'data': {"host": "192.168.1.103", 'port': 27018}},
        period=range(5, 21, 5)
    )

    print o
    # print pd.DataFrame(
    #     p.history
    # )

    # print pd.DataFrame(
    #     p.trades
    # )
