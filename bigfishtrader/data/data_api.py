import tushare
import json
import pandas as pd
import oandapy
from pandas_datareader.data import YahooDailyReader
from datetime import datetime
from threading import Thread
try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty


class DataCollector(object):
    trans_map = {
        'yahoo': {'Date': 'datetime',
                  'Close': 'close',
                  'High': 'high',
                  'Low': 'low',
                  'Open': 'open',
                  'Volume': 'volume'}
    }

    def __init__(self, **setting):
        from pymongo import MongoClient

        db = setting.pop('db')
        users = setting.pop('user', {})
        self.client = MongoClient(**setting)
        self.db = self.client[db]

        for db in users:
            self.client[db].authenticate(users[db]['id'], users[db]['password'])

        self._running = False
        self.queue = Queue()
        self._threads = {}

    def save(self, col_name, data, db=None):
        data = [doc.to_dict() for index, doc in data.iterrows()] if isinstance(data, pd.DataFrame) else data

        db = self.client[db] if db else self.db

        result = db[col_name].delete_many(
            {'datetime': {'$gte': data[0]['datetime'], '$lte': data[1]['datetime']}}
        )

        db[col_name].insert(data)
        db[col_name].create_index('datetime')
        return [col_name, data[0]['datetime'], data[-1]['datetime'], len(data), result.deleted_count]

    def run(self, function):
        while self._running or self.queue.qsize():
            try:
                params = self.queue.get(timeout=1)
            except Empty:
                continue
            result = function(**params)
            if result is not None:
                print(result)

    def start(self, function, t=5):
        self._running = True
        for i in range(0, t):
            thread = Thread(target=self.run, args=[function])
            thread.start()
            self._threads[thread.name] = thread

    def join(self):
        for name, thread in self._threads.items():
            thread.join()

        while len(self._threads):
            self._threads.popitem()

    def stop(self):
        self._running = False

    def read(self, col_name, db=None, start=None, end=None, length=None, **kwargs):
        db = self.client[db] if db else self.db

        if start:
            fter = {'datetime': {'$gte': start}}
            if end:
                fter['datetime']['$lte'] = end
            elif length:
                kwargs['limit'] = length
            kwargs['filter'] = fter
        elif length:
            kwargs['sort'] = [('datetime', -1)]
            kwargs['limit'] = length
            if end:
                kwargs['filter'] = {'datetime': {'$lte': end}}
        elif end:
            kwargs['filter'] = {'datetime': {'$lte': end}}

        data = pd.DataFrame(
            list(db[col_name].find(**kwargs))
        )

        for key, value in kwargs.get('sort', []):
            if value < 0:
                data = data.iloc[::-1]

        data.pop('_id')
        return data


class StockData(DataCollector):
    def __init__(self, host='localhost', port=27017, db='HS', user={}):
        super(StockData, self).__init__(host=host, port=port, db=db, user=user)

    def save_k_data(
            self, code=None, start='', end='',
            ktype='D', autype='qfq', index=False,
            retry_count=3, pause=0.001
    ):
        frame = tushare.get_k_data(
            code, start, end,
            ktype, autype, index,
            retry_count, pause
        )

        format_ = '%Y-%m-%d'
        if len(frame['date'].values[-1]) > 11:
            format_ = ' '.join((format_, '%H:%M'))

        frame['datetime'] = pd.to_datetime(
            frame.pop('date'),
            format=format_
        )

        frame.pop('code')

        self.save('.'.join((code, ktype)), frame)
        print (code, 'saved')

    def update(self, col_name):
        doc = self.db[col_name].find_one(sort=[('datetime', -1)])
        code, ktype = col_name.split('.')
        try:
            self.save_k_data(code, start=doc['datetime'].strftime('%Y-%m-%d %H:%M'), ktype=ktype)
        except IndexError:
            print (col_name, 'already updated')

    def update_all(self):
        for collection in self.db.collection_names():
            self.update(collection)

    def save_hs300(
            self, start='', end='',
            ktype='D', autype='qfq', index=False,
            retry_count=3, pause=0.001
        ):
        hs300 = tushare.get_hs300s()
        for code in hs300['code']:
            self.save_k_data(
                code, start, end,
                ktype, autype, index,
                retry_count, pause
            )

    def save_yahoo(self, symbols=None, start=None, end=None, retry_count=3,
                   pause=0.001, session=None, adjust_price=False, ret_index=False,
                   chunksize=25, interval='d', db='yahoo'):
        data = YahooDailyReader(symbols, start, end, retry_count, pause, session,
                                adjust_price, ret_index, chunksize, interval).read()
        data['datetime'] = data.index

        self.save('.'.join((symbols, interval)), data.rename_axis(self.trans_map['yahoo'], 1), db)


class OandaData(DataCollector):
    def __init__(self, oanda_info, host='localhost', port=27017, db='Oanda', user={}):
        """

        :param oanda_info: dict, oanda account info {'environment': 'practice', 'access_token': your access_token}
        :return:
        """

        super(OandaData, self).__init__(host=host, port=port, db='Oanda', user={})

        if isinstance(oanda_info, str):
            with open(oanda_info) as info:
                oanda_info = json.load(info)
                info.close()

        self.api = oandapy.API(oanda_info['environment'], oanda_info['access_token'])
        self.time_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        self.default_period = [
            'M15', 'M30', 'H1', 'H4', 'D', 'M'
        ]
        self.MAIN_CURRENCY = [
            'EUR_USD', 'AUD_USD', 'NZD_USD', 'GBP_USD', 'USD_CAD', 'USD_JPY'
        ]

    def get_history(self, instrument, **kwargs):
        data_type = kwargs.pop('data_type', 'dict')
        if isinstance(kwargs.get('start', None), datetime):
            kwargs['start'] = kwargs['start'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if isinstance(kwargs.get('end', None), datetime):
            kwargs['end'] = kwargs['end'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        kwargs.setdefault('candleFormat', 'midpoint')
        kwargs.setdefault('dailyAlignment', 0)
        kwargs.setdefault('alignmentTimezone', 'UTC')
        print('requiring', kwargs)

        result = self.api.get_history(instrument=instrument, **kwargs)

        for candle in result['candles']:
            candle['datetime'] = datetime.strptime(candle['time'], '%Y-%m-%dT%H:%M:%S.%fZ')

        if data_type == 'DataFrame':
            result['candles'] = pd.DataFrame(result['candles'])

        return result

    def save_history(self, instrument, **kwargs):
        try:
            result = self.get_history(instrument, **kwargs)
        except oandapy.OandaError as oe:
            print (oe.message)
            if oe.error_response['code'] == 36:
                return self.save_div(instrument, **kwargs)
            else:
                raise oe

        saved = self.save(
            '.'.join((result['instrument'], result['granularity'])),
            result['candles']
        )
        print(saved)

        return saved

    def save_div(self, instrument, **kwargs):
        if 'start' in kwargs:
            end = kwargs.pop('end', None)
            kwargs['count'] = 5000
            saved = self.save_history(instrument, **kwargs)

            kwargs.pop('count')
            if end:
                kwargs['end'] = end
            kwargs['start'] = saved[2]
            next_saved = self.save_history(instrument, **kwargs)
            saved[3] += next_saved[3]
            saved[4] += next_saved[4]
            saved[2] = next_saved[2]
            return saved
        else:
            raise ValueError('In save data mode, start is required')

    def save_many(self, instruments, granularity, start, end=None, t=5):
        if isinstance(instruments, list):
            if isinstance(granularity, list):
                self._save_many(
                    start, end, t,
                    [(i, g) for i in instruments for g in granularity]
                )

            else:
                self._save_many(
                    start, end, t,
                    [(i, granularity) for i in instruments]
                )

        else:
            if isinstance(granularity, list):
                self._save_manny(
                    start, end, t,
                    [(instruments, g) for g in granularity]
                )

            else:
                self.save_history(instruments, granularity=granularity, start=start, end=end)

    def _save_many(self, start, end, t, i_g):
        for i, g in i_g:
            self.queue.put({
                'instrument': i,
                'granularity': g,
                'start': start,
                'end': end
            })

        self.start(self.save_history, t)
        self.stop()
        self.join()

    def save_main(self):
        self.save_many(self.MAIN_CURRENCY, self.default_period, datetime(2010, 1, 1), datetime.now())

    def update(self, col_name):
        doc = self.db[col_name].find_one(sort=[('datetime', -1)], projection=['time'])
        if doc is None:
            raise ValueError('Unable to find the last record or collection: %s, '
                             'please check your DataBase' % col_name)

        i, g = col_name.split('.')
        return self.save_history(i, granularity=g, start=doc['time'], includeFirst=False)

    def update_many(self, col_names=[], t=5):
        if len(col_names) == 0:
            col_names = self.db.collection_names()

        for col_name in col_names:
            self.queue.put({'col_name': col_name})

        self.start(self.update, t)
        self.stop()
        self.join()
