from fxdayu.models.dao.base import ExecutionDataDao
from fxdayu.models.data import ExecutionData


@ExecutionDataDao.implement
class ExecutionDataDaoSqlAlchemy(ExecutionDataDao):
    def __init__(self, engine):
        super(ExecutionDataDaoSqlAlchemy, self).__init__()
        self.engine = engine

    def insert(self, execution, session=None):
        session = self.engine.session if session is None else session
        session.merge(execution)
        session.commit()

    def delete(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        session.query(ExecutionData).filter(
            ExecutionData.gateway == gateway,
            ExecutionData.account == account,
            ExecutionData.clOrdID == ord_id,
        ).delete()
        session.commit()

    def find(self, gateway, account, ord_id, session=None):
        session = self.engine.session if session is None else session
        return session.query(ExecutionData).filter(
            ExecutionData.gateway == gateway,
            ExecutionData.account == account,
            ExecutionData.clOrdID == ord_id,
        ).one_or_none()

    def find_all(self, session=None):
        session = self.engine.session if session is None else session
        return session.query(ExecutionData).filter().all()
