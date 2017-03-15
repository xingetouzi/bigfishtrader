# encoding:utf-8
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import *
import types


class Strategy(HandlerCompose):
    def __init__(self, event_queue, engine, context, data, portfolio, router, **kwargs):
        super(Strategy, self).__init__()
        self.event_queue = event_queue
        self.engine = engine
        self.context = context
        self.data = data
        self.portfolio = portfolio
        self.router = router
        for name, model in kwargs.items():
            self.__setattr__(name, model)

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=100)
        self._id = 0

    def init_params(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                self.__setattr__(key, value)

    @property
    def next_id(self):
        self._id += 1
        return self._id

    def initialize(self):
        """
        初始化设定
        :return:
        """

        raise NotImplementedError('Should implement initialize()')

    def handle_data(self):
        pass

    def on_time(self, event, kwargs=None):
        self.handle_data()

    def time_limit(self, func, topic='.', priority=100, **kw):
        def event_handler(event, kwargs=None):
            for key, value in kw.items():
                attr = getattr(self.context.current_time, key, None)
                if isinstance(attr, (types.MethodType, types.BuiltinMethodType,
                                     types.FunctionType, types.BuiltinFunctionType)):
                    attr = attr()
                if attr != value:
                    return
            func()

        self.engine.register(event_handler, EVENTS.TIME, topic, priority)

    def open_position(self, ticker, quantity, price=None, order_type=EVENTS.ORDER, **kwargs):
        local_id = self.next_id
        self.event_queue.put(
            OrderEvent(
                self.context.current_time,
                ticker, OPEN_ORDER, quantity, price,
                order_type=order_type,
                local_id=local_id,
                **kwargs
            )
        )
        return local_id

    def open_limit(self, ticker, quantity, price, **kwargs):
        return self.open_position(ticker, quantity, price, EVENTS.LIMIT, **kwargs)

    def open_stop(self, ticker, quantity, price, **kwargs):
        return self.open_position(ticker, quantity, price, EVENTS.STOP, **kwargs)

    def cancel_order(self, **conditions):
        self.event_queue.put(
            CancelEvent(**conditions)
        )

    def close_position(
            self, ticker=None, quantity=None, price=None,
            order_type=EVENTS.ORDER, position=None, **kwargs
    ):
        if position:
            if position.available:
                _id = position.position_id if position.position_id else self.next_id
                self.event_queue.put(
                    OrderEvent(
                        self.context.current_time,
                        position.ticker, CLOSE_ORDER,
                        position.available, price,
                        order_type=order_type,
                        local_id=_id
                    )
                )
                return _id
            else:
                print('position.available == 0 , unable to close position')

        elif ticker and quantity:
            for _id, available in self.portfolio.separate_close(ticker, quantity):
                self.event_queue.put(
                    OrderEvent(
                        self.context.current_time,
                        ticker, CLOSE_ORDER, available, price,
                        order_type=order_type, local_id=_id,
                        **kwargs
                    )
                )

    def close_limit(self, price, ticker=None, quantity=None, position=None):
        return self.close_position(ticker, quantity, price, EVENTS.LIMIT, position)

    def close_stop(self, price, ticker=None, quantity=None, position=None):
        return self.close_position(ticker, quantity, price, EVENTS.STOP, position)

    def set_commission(self, buy_cost=None, sell_cost=None, unit=None, min_cost=0, calculate_function=None):
        """
        佣金设置
        :param buy_cost: 买入(开仓)佣金
        :param sell_cost: 卖出(平仓)佣金
        :param unit:
            'value' : commission = price * quantity * (buy_cost or sell_cost)
            'share' : commission = quantity * (buy_cost or sell_cost)
        :param calculate_function:
            可自定义佣金计算方法，以order和price作为输入参数，返回佣金值
            sample:
            def calculation(order, price):
                return price * 0.0001
        :return:
        """
        exchange = self.router
        if exchange:
            if buy_cost and sell_cost and unit:
                if unit == 'value':
                    setattr(
                        exchange, "calculate_commission",
                        lambda order, price: max(
                            abs(order.quantity)*price*buy_cost if order.action
                            else abs(order.quantity)*price*sell_cost,
                            min_cost
                        )
                    )
                elif unit == 'share':
                    setattr(
                        exchange, "calculate_commission",
                        lambda order, price: max(
                            abs(order.quantity)*buy_cost if order.action
                            else abs(order.quantity)*sell_cost,
                            min_cost
                        )
                    )

            if calculate_function:
                setattr(exchange, "calculate_commission", calculate_function)

    def set_slippage(self, value=0, unit='pct', function=None):
        """
        滑点设置
        :param value: 滑点值
        :param unit:
            'pct': slippage = price * value
            'value': slippage = value
        :param function:
            可自定义滑点计算方法，以order和price作为输入参数，返回滑点值
            sample:
            def calculation(order, price):
                if order.quantity > 0:
                    return price * 0.0001
                else:
                    return -price * 0.0001
        :return:
        """
        exchange = self.router
        if exchange:
            if value and unit:
                if unit == 'pct':
                    setattr(
                        exchange, 'calculate_slippage',
                        lambda order, price: value*price if (order.quantity > 0 and order.action) or
                        (order.quantity < 0 and order.action == 0)
                        else -value*price
                    )
                elif unit == 'value':
                    setattr(
                        exchange, 'calculate_slippage',
                        lambda order, price: value if (order.quantity > 0 and order.action) or
                        (order.quantity < 0 and order.action == 0)
                        else -value
                    )
            elif function:
                setattr(exchange, 'calculate_slippage', function)
