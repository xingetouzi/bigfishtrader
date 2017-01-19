from bigfishtrader.portfolio.base import AbstractPortfolio
from bigfishtrader.portfolio.position import Position
from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import EVENTS
from dictproxyhack import dictproxy


class OandaPortfolio(AbstractPortfolio):
    def __init__(self, init_cash, data_support):
        super(OandaPortfolio, self).__init__()
        self._cash = init_cash
        self.init_cash = init_cash
        self.data = data_support
        self.equity = init_cash
        self._positions = {}
        self.closed_positions = []
        self.history = []
        self._handlers['on_fill'] = Handler(self._on_fill, EVENTS.FILL, 'oanda')
        self._handlers['on_time'] = Handler(self._on_time, EVENTS.TIME)
        self._handlers['on_exit'] = Handler(self._trade_stop, EVENTS.EXIT)

    def _trade_stop(self, event, kwargs=None):
        for _id, position in self._positions:
            current = self.data.current(position.ticker)
            position.close(current['close'], current['time'], 0)
            self._cash += position.deposit + position.profit

        self.equity = self._cash

    def _on_fill(self, event, kwargs=None):
        if event.action:
            position = Position(
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
                elif abs(event.quantity) < abs(position.quantity):
                    new = position.separate(event.quantity, event.price)
                    new.close(event.price, event.time, event.commission)
                    self._cash += new.deposit + new.profit - event.commission
                    self.closed_positions.append(new)

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