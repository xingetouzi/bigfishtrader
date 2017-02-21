# encoding: utf-8
from dictproxyhack import dictproxy

from bigfishtrader.portfolio.position import Order, Position, OrderHandler
from bigfishtrader.portfolio.base import AbstractPortfolio
from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import EVENTS, OPEN_ORDER, CLOSE_ORDER, OrderEvent
import pandas as pd


class PositionPortfolio(AbstractPortfolio):
    def __init__(self, event_queue, data, init_cash=100000):
        super(PositionPortfolio, self).__init__()
        self.event_queue = event_queue
        self._data = data
        self._cash = init_cash
        self.init_cash = init_cash
        self._positions = {}
        self._history_positions = []
        self._trades = []
        self._orders = []
        self._info = []
        self._id = 0

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=150)
        self._handlers['on_recall'] = Handler(self.on_recall, EVENTS.RECALL, priority=150)
        self._handlers['on_fill'] = Handler(self.on_fill, EVENTS.FILL, topic='', priority=100)
        self._handlers['on_exit'] = Handler(self.on_exit, EVENTS.EXIT, priority=200)

    @property
    def next_id(self):
        self._id += 1
        return self._id

    @property
    def positions(self):
        return self._positions

    @property
    def history(self):
        return self._history_positions

    @property
    def trades(self):
        return self._trades

    @property
    def consignations(self):
        return self._orders

    @property
    def cash(self):
        return self._cash

    @property
    def security(self):
        return dict([(ticker, position.available) for ticker, position in self._positions.items()])

    @property
    def equity(self):
        return self._cash + sum(map(lambda p: p.value, self._positions.values()))

    @property
    def info(self):
        return self._info

    def on_time(self, event, kwargs=None):
        for ticker, position in self._positions.items():
            close = self._data.current(ticker).close
            if close == close:
                position.price = close
            show = position.show('ticker', 'quantity', 'price', 'profit', 'value', 'cost_price', 'commission')
            show['datetime'] = event.time
            self._history_positions.append(show)

        self._info.append(
            {'datetime': event.time, 'cash': self._cash, 'equity': self.equity},
        )

    def on_fill(self, event, kwargs=None):
        if event.action:
            self.open_position(
                event.time, event.ticker,
                event.quantity, event.price,
                event.commission
            )
        else:
            self.close_position(
                event.time, event.ticker,
                event.quantity, event.price,
                event.commission
            )

    def on_recall(self, event, kwargs=None):
        order = event.order
        if event.lock:
            position = self._positions.get(order.ticker, None)
            if position:
                position.lock(order.quantity)
        else:
            position = self._positions.get(order.ticker, None)
            if position:
                position.unlock(order.quantity)

    def on_exit(self, event, kwargs=None):
        for ticker, position in self._positions.items():
            self.close_position(
                self._data.current_time, ticker, position.quantity, position.price
            )

    def open_position(self, timestamp, ticker, quantity, price, commission=0, **kwargs):
        position = Position(ticker, quantity, price, commission, **kwargs)
        self._cash -= (position.cost + commission)

        old = self._positions.get(ticker, None)
        if old:
            old += position
        else:
            self._positions[ticker] = position

        self._trades.append(
            {'datetime': timestamp, 'ticker': ticker, 'quantity': quantity,
             'price': price, 'commission': commission, 'action': 'open'},
        )

    def close_position(self, timestamp, ticker, quantity, price, commission=0):
        position = self._positions.get(ticker, None)
        if position:
            self._cash += position.close(price, quantity, commission) - commission
            if position.quantity == 0:
                self._positions.pop(ticker)
            self._trades.append(
                {'datetime': timestamp, 'ticker': ticker, 'quantity': quantity,
                 'price': price, 'commission': commission ,'action': 'close'},
            )

    def send_open(self, ticker, quantity, price=None, order_type=EVENTS.ORDER, **kwargs):
        """
        开仓

        :param ticker: str, 品种名
        :param quantity: float or int, 数量
        :param price: float or int, 目标价, 如果是市价单可缺省
        :param order_type: enum, 下单类型
            EVENTS.ORDER: 市价单
            EVENTS.LIMIT: 限价单
            EVENTS.STOP: 停损单
        :param kwargs: 其他信息
        :return:
        """
        local_id = self.next_id
        self.event_queue.put(
            OrderEvent(
                self._data.current_time,
                ticker, OPEN_ORDER, quantity, price,
                order_type=order_type,
                local_id=local_id,
                **kwargs
            )
        )
        return local_id

    def send_close(self, ticker, quantity=None, price=None, order_type=EVENTS.ORDER, **kwargs):
        """
        平仓

        :param ticker: str, 品种名
        :param quantity: float or int, 数量, 如果缺省则平掉全部当前可交易的仓位
        :param price: float or int, 目标价, 如果是市价单可缺省
        :param order_type: enum, 下单类型
            EVENTS.ORDER: 市价单
            EVENTS.LIMIT: 限价单
            EVENTS.STOP: 停损单
        :param kwargs: 其他信息
        :return:
        """
        position = self._positions.get(ticker, None)
        if position:
            available = position.available
            if not available:
                print "available quantity of %s is 0" % ticker
                return

            if quantity:
                if quantity * available <= 0:
                    pass
                elif abs(quantity) > abs(available):
                    quantity = available
            else:
                quantity = available

            self.event_queue.put(
                OrderEvent(
                    self._data.current_time, ticker, CLOSE_ORDER,
                    quantity, price, order_type, local_id=self.next_id,
                    **kwargs
                )
            )


class OrderPortfolio(AbstractPortfolio):
    def __init__(self, event_queue, data, position_handler=None, init_cash=100000):
        super(OrderPortfolio, self).__init__()
        self.event_queue = event_queue
        self._data = data
        self._cash = init_cash
        self.init_cash = init_cash
        self._history = []
        self._trades = []
        self._info = []
        self.closed_positions = []
        self._id = 0
        if position_handler:
            self._orders = position_handler
        else:
            self._orders = OrderHandler()
            self._handlers['on_recall'] = Handler(self._orders.on_recall, EVENTS.RECALL)

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=150)
        self._handlers['on_fill'] = Handler(self.on_fill, EVENTS.FILL, topic='', priority=100)
        self._handlers['on_exit'] = Handler(self.close_at_stop, EVENTS.EXIT, priority=200)

    @property
    def next_id(self):
        self._id += 1
        return self._id

    @property
    def positions(self):
        return dictproxy(self._orders())

    @property
    def cash(self):
        return self._cash

    @property
    def equity(self):
        return self._cash + sum(
            map(
                lambda position: position.profit + position.deposit,
                self._orders().values()
            )
        )

    @property
    def security(self):
        return self._orders.security

    @property
    def info(self):
        return self._info

    @property
    def history(self):
        return self._history

    def on_time(self, event, kwargs=None):
        self._time = event.time
        for order in self._orders().values():
            close = self._data.current(order.ticker).close
            if close == close:
                order.update(close)
            show = order.show('ticker', 'open_time', 'open_price', 'quantity', 'deposit', 'commission', 'profit')
            show['datetime'] = event.time
            self._history.append(show)
        self.log()

    def log(self):
        """
        log portfolio's equity and cash.

        Returns:
            None
        """
        self._info.append({'datetime': self._time, 'equity': self.equity, 'cash': self._cash})

    def on_fill(self, event, kwargs=None):
        if event.action:
            self.open_position(
                event.position_id, event.ticker, event.price,
                event.quantity, event.time, event.commission,
                deposit_rate=event.deposit_rate, lever=event.lever
            )
        else:
            self.close_position(
                event.position_id, event.price,
                event.quantity, event.time,
                event.commission, event.external_id
            )

    def open_position(self, order_id, ticker, price, quantity, open_time, commission=0, **kwargs):
        position = Order(
            ticker, price, quantity, open_time,
            commission, order_id=order_id, **kwargs
        )

        if self._cash >= (position.deposit + commission):
            self._cash -= (position.deposit + commission)
            self._orders[position.position_id] = position
            self._trades.append({'datetime': open_time, 'action': 'close',
                                 'commission': commission, 'price': price,
                                 'ticker': position.ticker, 'quantity': quantity})


    def close_position(self, order_id, price, quantity, close_time, commission=0, new_id=None):
        position = self._orders.pop(order_id)

        if position:
            if position.quantity * quantity <= 0:
                raise ValueError(
                    'position.quantity and quantity should both be positive or negative'
                )

            if position.quantity == quantity:
                position.close(price, close_time, commission)
                self._cash += position.deposit + position.profit - commission
                self.closed_positions.append(position)

            elif abs(position.quantity) > abs(quantity):
                closed = position.separate(quantity, price, new_id)
                closed.close(price, close_time, commission)
                self._cash += closed.deposit + closed.profit - commission
                self.closed_positions.append(closed)
                self._orders[position.position_id] = position

            else:
                raise ValueError(
                    'quantity to be close is larger than position.quantity'
                )

            self._trades.append({'datetime': close_time, 'action': 'close',
                                 'commission': commission, 'price': price,
                                 'ticker': position.ticker, 'quantity': quantity})

    def separate_close(self, ticker, quantity):
        return self._orders.separate_close(ticker, quantity)

    def close_at_stop(self, event, kwargs=None):
        while len(self._orders):
            _id, position = self._orders.pop_item()
            position.close(position.price, self._time)
            self.closed_positions.append(position)

    def send_open(self, ticker, quantity, price=None, order_type=EVENTS.ORDER, **kwargs):
        local_id = self.next_id
        self.event_queue.put(
            OrderEvent(
                self._data.current_time,
                ticker, OPEN_ORDER, quantity, price,
                order_type=order_type,
                local_id=local_id,
                **kwargs
            )
        )
        return local_id

    def send_close(self, order_id=None, ticker=None, quantity=None, price=None, order_type=EVENTS.ORDER, **kwargs):
        """

        :param order_id: int, 订单号, 按指定的订单号平仓
        :param ticker: str, 持仓品种, 平掉该品种的仓位, 但实际上还是以订单的方式平仓
        order_id 和 ticker 需输入一个

        :param quantity: float or int, 数量
        :param price: float or int, 目标价, 如果是市价单可缺省
        :param order_type: enum, 下单类型
            EVENTS.ORDER: 市价单
            EVENTS.LIMIT: 限价单
            EVENTS.STOP: 停损单
        :param kwargs: 其他信息
        :return:
        """
        if order_id:
            order = self._orders[order_id]
            if order.available:
                self.event_queue.put(
                    OrderEvent(
                        self._data.current_time,
                        order.ticker, CLOSE_ORDER,
                        order.available, price,
                        order_type=order_type,
                        local_id=order_id,
                        **kwargs
                    )
                )
                return order_id
            else:
                print('position.available == 0 , unable to close position')
        elif ticker and quantity:
            for _id, available in self.separate_close(ticker, quantity):
                self.event_queue.put(
                    OrderEvent(
                        self._data.current_time,
                        ticker, CLOSE_ORDER, available, price,
                        order_type=order_type, local_id=_id,
                        **kwargs
                    )
                )