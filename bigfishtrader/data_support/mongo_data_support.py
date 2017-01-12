from bigfishtrader.data_support.base import AbstractDataSupport
from bigfishtrader.core import Handler
from bigfishtrader.event import EVENTS
import pandas as pd


class MongoDataSupport(AbstractDataSupport):
    def __init__(self, mongo_client=None, **colections):
        super(MongoDataSupport, self).__init__()
        self.__client = mongo_client
        self.__collections = colections
        self.__instance = {}
        self.__time = None
        self.__current = {}
        self._handlers['on_bar'] = Handler(self.on_bar, EVENTS.BAR, topic="", priority=100)

    def current(self, ticker, filed=None):
        return self.__current[ticker]

    def instance(
            self, ticker, period, filed,
            start=None, end=None, length=None
    ):
        ticker_period = '.'.join([ticker, period])
        instance = self.__instance.get(ticker_period, None)
        return self._get_from_instance(
            instance, filed, start, end, length
        )

    def history(
            self, ticker, period, filed,
            start=None, end=None, length=None,
            ticker_type=None
    ):
        ticker_period = '.'.join([ticker, period])
        # instance = self.__instance.get(ticker_period, None)
        # if instance is not None:
        #     return self._get_from_instance(
        #         instance, filed, start, end, length
        #     )
        # else:
        return self._get_from_database(
            ticker_period, filed, ticker_type, start, end, length
        )

    def _get_from_instance(
            self, instance, filed,
            start=None, end=None, length=None
    ):
        if start and end:
            return instance[
                (instance.datetime >= start) and (instance.datetime <= end)
            ][filed]
        elif start and length:
            return instance[
                instance.datetime >= start
            ][filed].head(length)
        elif end and length:
            return instance[
                instance.datetime <= end
            ][filed].tail(length)
        elif length:
            return instance[
                instance.datetime <= self.__time
            ][filed].tail(length)
        else:
            return instance.copy()

    def _get_from_database(
            self, col_name, filed, ticker_type=None,
            start=None, end=None, length=None
    ):
        collection = self.__collections.get(col_name, None)
        if not collection:
            collection = self.__client[ticker_type][col_name]

        dt_filter = {}
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        Filter = {'datetime': dt_filter} if len(dt_filter) else {}

        frame = pd.DataFrame(
            list(
                collection.find(
                    Filter, projection=filed
                ).sort([('datetime', 1)])
            )
        ) if len(dt_filter) == 2 else pd.DataFrame(
            list(
                collection.find(
                    Filter, projection=filed
                ).sort([('datetime', 1)]).limit(length)
            )
        )

        frame.pop('_id')
        return frame

    def set_collections(self, col_name, db):
        self.__collections[col_name] = self.__client[db][col_name]

    def set_instance(self, ticker_period, frame_data=None):
        if frame_data is not None:
            self.__instance[ticker_period] = frame_data
        else:
            self.__instance[ticker_period] = pd.DataFrame

    def on_bar(self, event, kwargs=None):
        self.__time = event.time
        self.__current[event.ticker] = event

    @property
    def current_time(self):
        return self.__time

if __name__ == '__main__':
    pass
