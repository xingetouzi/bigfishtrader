from collections import defaultdict


class DataDao(object):
    IMPLEMENTS = defaultdict(list)

    @classmethod
    def implement(cls, implement):
        cls.IMPLEMENTS[cls.__name__].append(implement)
        return implement

    @classmethod
    def implements(cls):
        return cls.IMPLEMENTS[cls.__name__]

    @staticmethod
    def match(url):
        return True


class PositionDataDao(DataDao):
    def insert(self, position, session=None):
        raise NotImplementedError

    def delete(self, gateway, account, symbol, session=None):
        raise NotImplementedError

    def find(self, gateway, account, symbol, session=None):
        raise NotImplementedError

    def find_by_account(self, gateway, account, session=None):
        raise NotImplementedError

    def find_all(self, session=None):
        raise NotImplementedError


class AccountDataDao(DataDao):
    def insert(self, account, session=None):
        raise NotImplementedError

    def delete(self, gateway, account, session=None):
        raise NotImplementedError

    def find(self, gateway, account, session=None):
        raise NotImplementedError

    def find_all(self, gateway, session=None):
        raise NotImplementedError


class ExecutionDataDao(DataDao):
    def insert(self, execution, session=None):
        raise NotImplementedError

    def delete(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find_all(self, session=None):
        raise NotImplementedError


class OrderReqDao(DataDao):
    def insert(self, order_req, session=None):
        raise NotImplementedError

    def delete(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find_all(self, session=None):
        raise NotImplementedError


class OrderStatusDataDao(DataDao):
    def insert(self, order_status, session=None):
        raise NotImplementedError

    def delete(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find(self, gateway, account, ord_id, session=None):
        raise NotImplementedError

    def find_all(self, session=None):
        raise NotImplementedError
