from bigfishtrader.operation import *
from datetime import datetime


period = 10


def initialize(context, data):
    data.init(['000001', '000002'], 'D', start=datetime(2010, 1, 1), end=datetime(2016, 12, 31))


def handle_data(context, data):
    time = context.current_time
    if (time.isoweekday() == 1) and (time.day <= 7):

        security = get_security()
        s1 = security.get('000001', 0)
        s2 = security.get('000002', 0)
        history = data.history(['000001', '000002'], frequency='D', fields='close', length=period)
        if len(history) < period:
            return

        h1 = history['000001']
        h2 = history['000002']

        if s1:
            if (h1.values[-1] - h1.values[0])/h1.values[-1] < (h2.values[-1] - h2.values[0])/h2.values[-1]:
                close_position('000001', s1)
                open_position('000002', 1000)

        elif s2:
            if (h1.values[-1] - h1.values[0])/h1.values[-1] > (h2.values[-1] - h2.values[0])/h2.values[-1]:
                close_position('000002', s2)
                open_position('000001', 1000)
        else:
            if (h1.values[-1] - h1.values[0])/h1.values[-1] < (h2.values[-1] - h2.values[0])/h2.values[-1]:
                open_position('000002', 1000)
            else:
                open_position('000001', 1000)




