from pymongo import MongoClient
import json


def connect(**info):
    users = info.pop('user', {})
    client = MongoClient(**info)

    for db in users:
        client[db].authenticate(users[db]['id'], users[db]['password'])

    return client


def client_from_json(filepath):
    info = json.load(open(filepath))
    return connect(**info)
