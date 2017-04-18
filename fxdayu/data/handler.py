# encoding:utf-8
from pymongo.mongo_client import database
import pandas as pd
import pymongo


class DataHandler(object):

    def write(self, *args, **kwargs):
        pass

    def read(self, *args, **kwargs):
        pass

    def inplace(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def table_names(self, *args, **kwargs):
        pass


class MongoHandler(DataHandler):

    def __init__(self, host='localhost', port=27017, users=None, db=None, **kwargs):
        self.client = pymongo.MongoClient(host, port, **kwargs)
        self.db = self.client[db] if db else None

        if isinstance(users, dict):
            for db in users:
                self.client[db].authenticate(users[db]['id'], users[db]['password'])

    def _locate(self, collection, db=None):
        if isinstance(collection, database.Collection):
            return collection
        else:
            if db is None:
                return self.db[collection]
            elif isinstance(db, database.Database):
                return db[collection]
            else:
                return self.client[db][collection]

    def write(self, data, collection, db=None, index=None):
        """

        :param data(DataFrame|list(dict)): 要存的数据
        :param collection(str): 表名
        :param db(str): 数据库名
        :param index(str): 以index值建索引, None不建索引
        :return:
        """
        collection = self._locate(collection, db)
        data = self.normalize(data, index)
        collection.insert_many(data)
        if index:
            collection.create_index(index)
        return {'collection': collection.name, 'start': data[0], 'end': data[-1]}

    def read(self, collection, db=None, index='datetime', start=None, end=None, length=None, **kwargs):
        """

        :param collection(str): 表名
        :param db(str): 数据库名
        :param index(str): 读取索引方式
        :param start(datetime):
        :param end(datetime):
        :param length(int):
        :param kwargs:
        :return:
        """

        if index:
            if start:
                fter = {index: {'$gte': start}}
                if end:
                    fter[index]['$lte'] = end
                elif length:
                    kwargs['limit'] = length
                kwargs['filter'] = fter
            elif length:
                kwargs['sort'] = [(index, -1)]
                kwargs['limit'] = length
                if end:
                    kwargs['filter'] = {index: {'$lte': end}}
            elif end:
                kwargs['filter'] = {index: {'$lte': end}}

        db = self.db if db is None else self.client[db]

        if isinstance(collection, str):
            return self._read(db[collection], index, **kwargs)
        if isinstance(collection, database.Collection):
            return self._read(collection, index, **kwargs)
        elif isinstance(collection, (list, tuple)):
            panel = {}
            for col in collection:
                try:
                    if isinstance(col, database.Collection):
                        panel[col.name] = self._read(col, index, **kwargs)
                    else:
                        panel[col] = self._read(db[col], index, **kwargs)
                except KeyError as ke:
                    if index in str(ke):
                        pass
                    else:
                        raise ke
            return pd.Panel.from_dict(panel)
        else:
            return self._read(db[collection], index, **kwargs)

    @staticmethod
    def _read(collection, index=None, **kwargs):
        data = list(collection.find(**kwargs))

        for key, value in kwargs.get('sort', []):
            if value < 0:
                data.reverse()
        data = pd.DataFrame(data)

        if index:
            data.index = data.pop(index)

        if len(data):
            data.pop('_id')

        return data

    def inplace(self, data, collection, db=None, index='datetime'):
        """
        以替换的方式存(存入不重复)

        :param data(DataFrame|list(dict)): 要存的数据
        :param collection(str): 表名
        :param db(str): 数据库名
        :param index(str): 默认以datetime为索引替换
        :return:
        """

        collection = self._locate(collection, db)
        data = self.normalize(data, index)

        collection.delete_many({index: {'$gte': data[0][index], '$lte': data[-1][index]}})
        collection.insert_many(data)
        collection.create_index(index)
        return {'collection': collection.name, 'start': data[0], 'end': data[-1]}

    def update(self, data, collection, db=None, index='datetime', how='$set'):
        collection = self._locate(collection, db)

        if isinstance(data, pd.DataFrame):
            if index in data.columns:
                data.index = data[index]
            for name, doc in data.iterrows():
                collection.update_one({index: name}, {how: doc.to_dict()})
        else:
            for doc in data:
                collection.update_one({index: doc.pop(index)}, doc)

    def delete(self, filter, collection, db=None):
        collection = self._locate(collection, db)
        collection.delete_many(filter)

    def normalize(self, data, index=None):
        if isinstance(data, pd.DataFrame):
            if index and (index not in data.columns):
                data[index] = data.index
            return [doc[1].to_dict() for doc in data.iterrows()]
        elif isinstance(data, dict):
            key, value = list(map(lambda *args: args, *data.iteritems()))
            return list(map(lambda *args: dict(map(lambda x, y: (x, y), key, args)), *value))
        elif isinstance(data, pd.Series):
            if data.name is None:
                raise ValueError('name of series: data is None')
            name = data.name
            if index is not None:
                return list(map(lambda k, v: {index: k, name: v}, data.index, data))
            else:
                return list(map(lambda v: {data.name: v}, data))
        else:
            return data

    def table_names(self, db=None):
        if not db:
            return self.db.collection_names()
        else:
            return self.client[db].collection_names()


from collections import Iterable
from datetime import datetime
from numpy import float64
import redis


class RedisHandler(DataHandler):

    def __init__(self, redis_client=None, transformer=None, **kwargs):
        self.client = redis_client if redis_client else redis.StrictRedis(**kwargs)
        self.transformer = {
            'datetime': lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
            'close': float64,
            'open': float64,
            'high': float64,
            'low': float64,
            'volume': float64
        } if transformer is None else transformer

        self.fields = self.transformer.keys()
        self.pubsub = self.client.pubsub()

    def trans(self, key, sequence):
        try:
            trans = self.transformer[key]
        except KeyError:
            return sequence

        if isinstance(sequence, str):
            return trans(sequence)
        elif isinstance(sequence, Iterable):
            return map(trans, sequence)
        else:
            return trans(sequence)

    @staticmethod
    def join(*args):
        return ':'.join(args)

    def read(self, name, index='datetime', start=None, end=None, length=None, fields=None):
        if not fields:
            fields = list(self.fields)
            fields.remove(index)
        loc, main_index = self._read_index(self.join(name, index), self.transformer[index], start, end, length)
        self.locate_read(name, loc, fields)

        return pd.DataFrame(self.locate_read(name, loc, fields), self.trans(index, main_index))

    @staticmethod
    def search_sorted(index, key, transform, reverse=False):
        if reverse:
            count = len(index)
            for i in reversed(index):
                count -= 1
                if key >= transform(i):
                    return count
            return count
        else:
            count = 0
            for i in index:
                if key <= transform(i):
                    return count
                count += 1
            return count

    def _read_index(self, key_index, transform, start=None, end=None, length=None):
        index = self.client.lrange(key_index, 0, -1)
        if start or end:
            if start:
                s = self.search_sorted(index, start, transform)
                if end:
                    e = self.search_sorted(index, end, transform, True)
                    return [s, e], index[s:e+1]
                elif length:
                    return [s, s+length-1], index[s:s+length]
                else:
                    return [s, -1], index[s:]
            else:
                e = self.search_sorted(index, end, transform, True)
                if length:
                    return [e-length+1, e], index[e-length+1:e+1]
                else:
                    return [0, e], index[0:e+1]
        else:
            if length:
                return [-length, -1], index[-length:]
            else:
                return [0, -1], index

    def write(self, data, name, index='datetime', pipeline=None):
        execute = False
        if pipeline is None:
            pipeline = self.client.pipeline()
            execute = True

        if isinstance(data, pd.DataFrame):
            if index in data.columns:
                pipeline.rpush(self.join(name, index), *data[index])
            else:
                pipeline.rpush(self.join(name, index), *data.index)
            for key, item in data.iteritems():
                pipeline.rpush(self.join(name, key), *item)
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float, unicode)):
                    pipeline.rpush(self.join(name, key), value)
                elif isinstance(value, Iterable):
                    pipeline.rpush(self.join(name, key), *value)
                else:
                    pipeline.rpush(self.join(name, key), value)
        else:
            return pipeline

        if execute:
            return pipeline.execute()
        else:
            return pipeline

    def inplace(self, data, name, index='datetime', pipeline=None):
        if isinstance(data, pd.DataFrame):
            pipeline = self.client.pipeline()

            return pipeline.execute()

    def update(self, data, name, index='datetime', pipeline=None):
        l_range = self.client.lrange(self.join(name, index), 0, -1)
        trans = self.transformer[index]
        if isinstance(data, dict):
            index_value = data.pop(index)
            loc = self.search_sorted(l_range, index_value, trans)
            if trans(l_range[loc]) == index_value:
                return self.locate_update(data, name, loc, pipeline)
        elif isinstance(data, pd.DataFrame):
            if index in data:
                data.index = data[index]

            execute = False
            if pipeline is None:
                pipeline = self.client.pipeline()
                execute = True
            for index_value, rows in data.iterrows():
                loc = self.search_sorted(l_range, index_value, trans)
                if trans(l_range[loc]) == index_value:
                    self.locate_update(rows.to_dict(), name, loc, pipeline)
            if execute:
                return pipeline.execute()
            else:
                return pipeline

    def locate_update(self, data, name, loc=-1, pipeline=None):
        if pipeline is not None:
            for key, value in data.items():
                pipeline.lset(self.join(self.join(name, key)), loc, value)
            return pipeline
        else:
            pipeline = self.client.pipeline()
            for key, value in data.items():
                pipeline.lset(self.join(self.join(name, key)), loc, value)
            return pipeline.execute()

    def locate_read(self, name, loc, fields=None):
        if fields is None:
            fields = self.fields

        if isinstance(loc, int):
            return {f: self.trans(f, self.client.lindex(self.join(name, f), loc)) for f in fields}
        elif isinstance(loc, slice):
            return {f: self.trans(f, self.client.lrange(self.join(name, f), loc.start, loc.stop)) for f in fields}
        elif isinstance(loc, (list, tuple)):
            return {f: self.trans(f, self.client.lrange(self.join(name, f), loc[0], loc[1])) for f in fields}
        else:
            return {f: self.trans(f, self.client.lrange(self.join(name, f), 0, -1)) for f in fields}

    def delete(self, name, fields=None):
        if fields is None:
            fields = self.fields
        return self.client.delete(*map(lambda x: self.join(name, x), fields))

    def subscribe(self, *args, **kwargs):
        self.pubsub.subscribe(*args, **kwargs)

    def listen(self, function):
        for data in self.pubsub.listen():
            function(data['data'])