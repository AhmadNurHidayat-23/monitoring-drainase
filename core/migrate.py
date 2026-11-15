from pathlib import Path
from sqlalchemy import create_engine,event
from .db import initialize,connect

def migrate(folder):
    from app.models import Base
    folder=Path(folder).resolve()
    initialize(folder)
    db=connect(folder)
    with db:
        if 'active' not in [r[1] for r in db.execute('PRAGMA table_info(users)')]:
            db.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
        db.execute('CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY)')
        db.execute('INSERT OR IGNORE INTO schema_version VALUES(1)')
    db.close()
    engine=create_engine('sqlite:///'+str(folder/'app.sqlite'),connect_args={'check_same_thread':False,'timeout':10})
    @event.listens_for(engine,'connect')
    def connection(dbapi,_record):
        dbapi.isolation_level=None
        dbapi.execute('PRAGMA foreign_keys=ON')
        dbapi.execute('PRAGMA journal_mode=WAL')
    @event.listens_for(engine,'begin')
    def begin(conn):
        conn.exec_driver_sql('BEGIN IMMEDIATE')
    Base.metadata.create_all(engine)
    return engine

if __name__=='__main__':
    import os
    migrate(os.getenv('APP_INSTANCE','./instance')).dispose()
    print('Inisialisasi SQLite dan model SQLAlchemy selesai.')
