# encoding: utf-8

from collections import OrderedDict

from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.const import GATEWAY
from bigfishtrader.event import EVENTS
from bigfishtrader.context import ContextMixin


class AccountMeta(object):
    @property
    def id(self):
        raise NotImplementedError

    @property
    def preBalance(self):
        raise NotImplementedError

    @property
    def balance(self):
        raise NotImplementedError

    @property
    def available(self):
        raise NotImplementedError

    @property
    def commission(self):
        raise NotImplementedError

    @property
    def closePnL(self):
        raise NotImplementedError

    @property
    def positionPnL(self):
        raise NotImplementedError


class Account(AccountMeta):
    __fields__ = ["id", "preBalance", "balance", "available", "commission",
                  "closePnL", "positionPnL"]

    def __init__(self, meta):
        """

        Args:
            meta(bigfishtrader.models.data.AccountData)

        Returns:

        """
        self._meta = meta

    @property
    def id(self):
        return self._meta.accountID

    @property
    def preBalance(self):
        return self._meta.preBalance

    @property
    def balance(self):
        return self._meta.balance

    @property
    def available(self):
        return self._meta.available

    @property
    def commission(self):
        return self._meta.margin

    @property
    def closePnL(self):
        return self._meta.closePnL

    @property
    def positionPnL(self):
        return self._meta.positionPnL

    def to_dict(self, ordered=False):
        if ordered:
            return OrderedDict([(attr, getattr(self, attr)) for attr in self.__fields__])
        else:
            return {attr: getattr(self, attr) for attr in self.__fields__}


class AccountGroup(AccountMeta):
    def __init__(self, main_id):
        super(AccountGroup, self).__init__()
        self._g = {}
        self._main_id = main_id

    def add(self, name, value):
        """

        Args:
            name:
            value(bigfishtrader.models.data.AccountData):

        Returns:

        """
        self._g[name] = value

    def remove(self, name):
        del self._g[name]

    @property
    def id(self):
        return self._main_id

    @property
    def preBalance(self):
        return reduce(lambda x, y: x + y.preBalance * y.exchangeRate, self._g.values(), 0)

    @property
    def balance(self):
        return reduce(lambda x, y: x + y.balance * y.exchangeRate, self._g.values(), 0)

    @property
    def available(self):
        return reduce(lambda x, y: x + y.available * y.exchangeRate, self._g.values(), 0)

    @property
    def margin(self):
        return reduce(lambda x, y: x + y.margin * y.exchangeRate, self._g.values(), 0)

    @property
    def commission(self):
        return reduce(lambda x, y: x + y.commission * y.exchangeRate, self._g.values(), 0)

    @property
    def positionPnL(self):
        return reduce(lambda x, y: x + y.positionPnL * y.exchangeRate, self._g.values(), 0)

    @property
    def closePnL(self):
        return reduce(lambda x, y: x + y.closePnL * y.exchangeRate, self._g.values(), 0)


class IBAccountGroup(AccountGroup):
    def __init__(self, main_id):
        super(IBAccountGroup, self).__init__(main_id)

    def add(self, name, value):
        if name != "BASE":
            super(IBAccountGroup, self).add(name, value)


# TODO 目前支持单账户，若要支持多账户，则AccountManager要管理所有的context，并将每个账户映射到每个context
class AccountHandler(HandlerCompose, ContextMixin):
    def __init__(self, context, environment):
        super(AccountHandler, self).__init__()
        ContextMixin.__init__(self, context, environment)
        self._account = None
        self._handlers = {
            "on_account_ib": Handler(self.on_account_ib, EVENTS.ACCOUNT, topic=GATEWAY.IB.value, priority=0)
        }

    def on_account_ib(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.AccountEvent):
            kwargs:

        Returns:

        """
        account = event.data
        main_id, child_id = account.accountID.split(".")
        if self._account is None:
            self.account = IBAccountGroup(main_id)
        self._account.add(child_id, account)

    @property
    def account(self):
        return self._account

    @account.setter
    def account(self, value):
        self._account = value
        self.context.account = value

    def link_context(self):
        pass
