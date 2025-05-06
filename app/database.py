from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

class DatabaseManager:
    def __init__(self):
        self.engine = self.create_engine()
        self.Session = sessionmaker(bind=self.engine) 

    def create_engine(self):
        """Return the SQLAlchemy engine connected to the DB."""
        connection_string = Config.get_connection_string()
        return create_engine(connection_string)

    def get_session(self):
        """Return a new session for querying."""
        return self.Session()

    def dispose(self):
        """Dispose of the engine to close any pooled connections."""
        self.engine.dispose()
