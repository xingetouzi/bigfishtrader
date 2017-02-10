import tushare
import json
import pandas as pd
import oandapy
from datetime import datetime
from threading import Thread
import requests
try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty


class DataCollector(object):
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

    def save(self, col_name, data):
        data = [doc.to_dict() for index, doc in data.iterrows()] if isinstance(data, pd.DataFrame) else data
        deleted = 0
        for doc in data:
            db_doc = self.db[col_name].find_one({'datetime': doc['datetime']})
            if db_doc:
                self.db[col_name].delete_one({'datetime': doc['datetime']})
                deleted += 1
            else:
                break
        for doc in reversed(data):
            db_doc = self.db[col_name].find_one({'datetime': doc['datetime']})
            if db_doc:
                self.db[col_name].delete_one({'datetime': doc['datetime']})
                deleted += 1
            else:
                break

        self.db[col_name].insert(data)
        self.db[col_name].create_index('datetime')
        return [col_name, data[0]['datetime'], data[-1]['datetime'], len(data), deleted]

    def run(self, function):
        while self._running or self.queue.qsize():
            try:
                params = self.queue.get(timeout=1)
            except Empty:
                continue
            result = function(**params)
            if result is not None:
                print result

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


class StockData(DataCollector):
    def __init__(self, **setting):
        setting.setdefault('db', 'HS')
        super(StockData, self).__init__(**setting)

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

    @staticmethod
    def get_yahoo_bar(code, retype='dict', start=None, end=None, **f):
        """

        :param code: stockCode (0700.hk, 600000.ss .....)
        :param f:
            a = begin month - 1
            b = begin day
            c = begin year
            d = end month - 1
            e = end day
            f = end year
            g = timeframe(w:week, d:day, w:week, m:month)
        :return: DataFrame, dict
        """

        if start:
            if isinstance(start, str):
                start = datetime.strptime(start, '%Y-%m-%d')
            elif not isinstance(start, datetime):
                raise TypeError("type of start must be datetime or str('YYYY-MM-DD')")
            f['a'] = start.month - 1
            f['b'] = start.day
            f['c'] = start.year

        if end:
            if isinstance(end, str):
                end = datetime.strptime(end, '%Y-%m-%d')
            elif not isinstance(end, datetime):
                raise TypeError("type of end must be datetime or str('YYYY-MM-DD')")
            f['d'] = end.month - 1
            f['e'] = end.day
            f['f'] = end.year

        print(code, f)

        url = "http://table.finance.yahoo.com/table.csv?s=%s" % code
        param = ''.join(map(lambda (key, value): '&%s=%s' % (key, value), f.items()))
        url += param + '&ignore=.csv'
        data = requests.get(url, timeout=10)
        lines = data.text.split('\n')
        lines.pop()
        columns = list(map(lambda w: w.lower(), lines[0].split(',')))
        docs = []
        for line in lines[1:]:
            line = line.split(',')
            doc = {'datetime': datetime.strptime(line[0], '%Y-%m-%d')}

            for i in range(1, len(columns)):
                doc[columns[i]] = float(line[i])
            if doc['volume'] == 0:
                continue

            docs.append(doc)

        docs.reverse()

        if retype == 'dict':
            return docs
        elif retype == 'DataFrame':
            return pd.DataFrame(docs)


class OandaData(DataCollector):
    def __init__(self, oanda_info, **setting):
        """

        :param oanda_info: dict, oanda account info {'environment': 'practice', 'access_token': your access_token}
        :param setting:
        :return:
        """

        setting.setdefault('db', 'Oanda')
        super(OandaData, self).__init__(**setting)

        if isinstance(oanda_info, str):
            with open(oanda_info) as info:
                oanda_info = json.load(info)
                info.close()

        self.api = oandapy.API(oanda_info['environment'], oanda_info['access_token'])
        self.account_id = oanda_info['account_id']
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
            print oe.message
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

    def save_manny(self, instruments, granularity, start, end=None, t=5):
        if isinstance(instruments, list):
            if isinstance(granularity, list):
                self._save_manny(
                    start, end, t,
                    [(i, g) for i in instruments for g in granularity]
                )

            else:
                self._save_manny(
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

    def _save_manny(self, start, end, t, i_g):
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
        self.save_manny(self.MAIN_CURRENCY, self.default_period, datetime(2010, 1, 1), datetime.now())

    def update(self, col_name):
        doc = self.db[col_name].find_one(sort=[('datetime', -1)], projection=['time'])
        if doc is None:
            raise ValueError('Unable to find the last record or collection: %s, '
                             'please check your DataBase' % col_name)

        i, g = col_name.split('.')
        return self.save_history(i, granularity=g, start=doc['time'], includeFirst=False)

    def update_manny(self, *col_names, **others):
        if len(col_names) == 0:
            col_names = self.db.collection_names()

        for col_name in col_names:
            self.queue.put({'col_name': col_name})

        self.start(self.update, others.pop('t', 5))
        self.stop()
        self.join()


if __name__ == '__main__':
    # oanda = OandaData("D:/bigfishtrader/bigfishtrader/router/oanda_account.json", db='Oanda')

    # oanda.save_main()

    stock = StockData(port=10001, db='stock_test')

    print stock.get_yahoo_bar('000002.sz', 'DataFrame', '2016-01-01')