from fxdayu.models.dao.base import PositionDataDao
from fxdayu.models.data import PositionData


@PositionDataDao.implement
class PositionDataDaoSqlAlchemy(PositionDataDao):
    def __init__(self, engine):
        self.engine = engine

    def insert(self, position, session=None):
        session = self.engine.session if session is None else session
        session.merge(position)
        session.commit()

    def delete(self, gateway, account, symbol, session=None):
        session = self.engine.session if session is None else session
        session.query(PositionData).filter(
            PositionData.gateway == gateway,
            PositionData.account == account,
            PositionData.symbol == symbol,
        ).delete()
        session.commit()

    def find(self, gateway, account, symbol, session=None):
        session = self.engine.session if session is None else session
        return session.query(PositionData).filter(
            PositionData.gateway == gateway,
            PositionData.account == account,
            PositionData.symbol == symbol,
        ).one_or_none()

    def find_by_account(self, gateway, account, session=None):
        session = self.engine.session if session is None else session
        return session.query(PositionData).filter(
            PositionData.gateway == gateway,
            PositionData.account == account,
        ).all()

    def find_all(self, session=None):
        session = self.engine.session if session is None else session
        return session.query(PositionData).all()
