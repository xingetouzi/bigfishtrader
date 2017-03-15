from fxdayu.portfolio.base import AbstractPortfolio
from fxdayu.portfolio.position import Order
from fxdayu.engine.handler import Handler
from fxdayu.event import EVENTS
from dictproxyhack import dictproxy
from datetime import datetime


class OandaPortfolio(AbstractPortfolio):
    def __init__(self, init_cash, data_support, client):
        super(OandaPortfolio, self).__init__()
        self._cash = init_cash
        self.init_cash = init_cash
        self.data = data_support
        self.equity = init_cash
        self._positions = {}
        self.closed_positions = []
        self.history = []
        self._handlers['on_fill'] = Handler(self._on_fill, EVENTS.EXECUTION, 'oanda')
        self._handlers['on_time'] = Handler(self._on_time, EVENTS.TIME)
        self._handlers['on_exit'] = Handler(self._trade_stop, EVENTS.EXIT)
        self._handlers['comfirm_trades'] = Handler(self.confirm_trades, EVENTS.CONFIRM, 'oanda_trades')
        self._handlers['comfirm_account'] = Handler(self.confirm_account, EVENTS.CONFIRM, 'oanda_acc')
        self.client = client

    def _trade_stop(self, event, kwargs=None):
        for _id, position in self._positions.items():
            current = self.data.current(position.ticker)
            position.close(current['close'], current['datetime'], 0)
            self._cash += position.deposit + position.profit
            self.closed_positions.append(position)

        self.equity = self._cash

    def _on_fill(self, event, kwargs=None):
        if event.action:
            position = Order(
                event.ticker, event.price, event.quantity,
                event.time, event.commission, event.lever,
                event.deposit_rate, event.position_id
            )
            self._positions[event.position_id] = position
            self._cash -= (position.deposit + position.commission)
        elif event.action == 0:
            position = self._positions.get(event.position_id, None)
            if position:
                if event.quantity == position.quantity:
                    position = self._positions.pop(event.position_id)
                    position.close(event.price, event.time, event.commission)
                    self._cash += position.deposit + position.profit - event.commission
                    self.closed_positions.append(position)
                    if self.client is not None:
                        self.client.Account['order'].insert_one(position.show())
                elif abs(event.quantity) < abs(position.quantity):
                    new = position.separate(event.quantity, event.price)
                    new.close(event.price, event.time, event.commission)
                    self._cash += new.deposit + new.profit - event.commission
                    self.closed_positions.append(new)
                    if self.client is not None:
                        self.client.Account['order'].insert_one(new.show())

    def _on_time(self, event, kwargs=None):
        self.equity = self._cash
        for position in self._positions.values():
            current = self.data.current(position.ticker)
            position.update(current['close'])
            self.equity += position.deposit + position.profit
        self.history.append(
            {'datetime': event.time, 'cash': self._cash, 'equity': self.equity}
        )

    @property
    def positions(self):
        return dictproxy(self._positions)

    @property
    def cash(self):
        return dictproxy(self._cash)

    def get_security(self, *args):
        security = {}
        for key in args:
            position = self._positions.get(key, None)
            if position:
                security[key] = {'ticker': position.ticker, 'quantity': position.quantity}

        if not len(args):
            for key, position in self._positions.items():
                security[key] = {'ticker': position.ticker, 'quantity': position.quantity}

        return security

    def confirm_trades(self, event, kwargs=None):
        trade = event.info
        quantity = trade['units']
        if trade['side'] == 'sell':
            quantity = -quantity
        self._positions[trade['id']] = Order(
            str(trade['instrument']), trade['price'], quantity,
            datetime.strptime(trade['time'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            lever=trade['lever'], deposit_rate=trade['deposit_rate'], order_id=trade['id']
        )

    def confirm_account(self, event, kwargs=None):
        account = event.info
        self._cash = account['marginAvail']
        self.client.Account['equity'].insert_one({'datetime': event.time, 'equity': account['balance']})
