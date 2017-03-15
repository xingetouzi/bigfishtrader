from fxdayu.api import order


def initialize(context, data):
    context.symbol = symbol("EUR.USD")
    subscribe(context.symbol)
    context.last_trade_time = time.time()


def handle_data(context, data):
    portfolio = context.portfolio
    if time.time() - context.last_trade_time >= 2:
        position = portfolio.positions.get(context.symbol.sid, None)
        if position:
            print("P: %s, %s" % (position.volume, position.frozenVolume))
        else:
            print("P: 0, 0")
        if position and position.volume > 0:
            order(context.symbol.sid, -20000, style=MarketOrder())
            context.last_trade_time = time.time()
            print("SELL")
        else:
            order(context.symbol.sid, 20000)
            context.last_trade_time = time.time()
            print("BUY")
