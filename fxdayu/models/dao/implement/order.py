from fxdayu.models.dao.base import OrderStatusDataDao, OrderReqDao
from fxdayu.models.order import OrderReq, OrderStatusData


@OrderStatusDataDao.implement
class OrderStatusDataDaoSqlAlchemy(OrderStatusDataDao):
    def __init__(self, engine):
        super(OrderStatusDataDaoSqlAlchemy, self).__init__()
        self.engine = engine

    def insert(self, order_status, session=None):
        session = self.engine.session if session is None else session
        session.merge(order_status)
        session.commit()

    def delete(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        session.query(OrderStatusData).filter(
            OrderStatusData.gateway == gateway,
            OrderStatusData.account == account,
            OrderStatusData.clOrdID == ord_id,
        ).delete()
        session.commit()

    def find(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        return session.query(OrderStatusData).filter(
            OrderStatusData.gateway == gateway,
            OrderStatusData.account == account,
            OrderStatusData.clOrdID == ord_id
        ).one_or_none()

    def find_all(self, session=None):
        session = self.engine.session if session is None else session
        return session.query(OrderStatusData).all()


@OrderReqDao.implement
class OrderReqDaoSqlAlchemy(OrderReqDao):
    def __init__(self, engine):
        super(OrderReqDaoSqlAlchemy, self).__init__()
        self.engine = engine

    def insert(self, order_req, session=None):
        session = self.engine.session if session is None else session
        session.merge(order_req)
        session.commit()

    def delete(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        session.query(OrderReq).filter(
            OrderReq.gateway == gateway,
            OrderReq.account == account,
            OrderReq.clOrdID == ord_id,
        ).delete()
        session.commit()

    def find(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        return session.query(OrderReq).filter(
            OrderReq.gateway == gateway,
            OrderReq.account == account,
            OrderReq.clOrdID == ord_id,
        ).one_or_none()

    def find_all(self, session=None):
        session = self.engine.session if session is None else session
        return session.query(OrderReq).all()
