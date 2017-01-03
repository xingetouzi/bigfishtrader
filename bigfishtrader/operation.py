from bigfishtrader.event import *

def initialize_operation(queue,handler,portfolio):
    global event_queue,price_handler
    event_queue=queue
    price_handler=handler

def current_time():
    return price_handler.get_last_time()

def open_position(price,ticker,quantity):
    event_queue.put(
        OrderEvent(
            price_handler.get_last_time(),
            ticker,OPEN_ORDER,quantity,price
        )
    )

def close_position(price,ticker=None,quantity=None,position=None):

    if position:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                position.ticker,CLOSE_ORDER,position.quantity,price
            )
        )
    else:
        event_queue.put(
            OrderEvent(
                price_handler.get_last_time(),
                ticker,CLOSE_ORDER,quantity,price
            )
        )


