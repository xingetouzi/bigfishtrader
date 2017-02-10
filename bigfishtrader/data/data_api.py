import tushare
from bigfishtrader.data.base import DataCollector
import pandas as pd


class TushareData(DataCollector):
    def __init__(self, **setting):
        super(TushareData, self).__init__(**setting)

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

    def save(self, col_name, data):
        if isinstance(data, pd.DataFrame):
            self.db[col_name].insert([doc.to_dict() for index, doc in data.iterrows()])
            print (col_name, 'saved')
        elif isinstance(data, list):
            self.db[col_name].insert(data)
            print (col_name, 'saved')
        else:
            raise TypeError('type(data) must be DataFrame or list')

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


if __name__ == '__main__':
    td = TushareData(port=10001, db='ts_test')
    td.update_all()
