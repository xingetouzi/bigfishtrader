from bigfishtrader.event import *


def initialize_operation(queue,handler,portfolio):
    global event_queue,price_handler,default_ticker,account
    event_queue=queue
    price_handler=handler
    default_ticker=handler.ticker
    account=portfolio

def ticker():
    return default_ticker


def current_time():
    return price_handler.get_last_time()

def open_position(price,ticker,quantity,order_type=ORDER):
    event_queue.put(
        OrderEvent(
            price_handler.get_last_time(),
            ticker,OPEN_ORDER,quantity,price,order_type
        )
    )


def cancel_order(**conditions):
    event_queue.put(
        CancelEvent(**conditions)
    )

def close_position(price,ticker=None,quantity=None,order_type=ORDER,position=None):
    if position:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                position.ticker, CLOSE_ORDER, position.quantity, price
            )
        )
    else:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                ticker, CLOSE_ORDER, quantity, price
            )
        )
