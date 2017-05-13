from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from fxdayu.context import ContextMixin
from fxdayu.models.dao.table import Base
import fxdayu.models.dao.base
import fxdayu.models.dao.implement


class PersistenceEngine(ContextMixin):
    def __init__(self, url="sqlite:///:memory:"):
        ContextMixin.__init__(self, use_proxy=True)
        self._url = url
        self.db_engine = create_engine(url)
        self.scoped_session = scoped_session(sessionmaker(bind=self.db_engine))
        self._initialized = False

    def _initialize(self):
        self._initialized = True
        Base.metadata.create_all(self.db_engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.scoped_session()
        if not self._initialized:
            self._initialize()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            pass

    @property
    def session(self):
        if not self._initialized:
            self._initialize()
        return self.scoped_session()

    def get_dao(self, cls):
        dao = getattr(fxdayu.models.dao.base, cls.__name__ + "Dao")
        for implement in dao.implements():
            if implement.match(self._url):
                return implement(self)

    def close(self):
        self.scoped_session.remove()

    def link_context(self):
        self.environment["persistence"] = self
