from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class LocationZone(Base):
    __tablename__ = 'location_zones'
    
    id = Column(Integer, primary_key=True)
    suburb = Column(String(length=128), nullable=False)
    town = Column(String(length=92), nullable=False)
    city_district = Column(String(length=92), nullable=True)
    city = Column(String(length=92), nullable=True)
    county = Column(String(length=92), nullable=False)
    state = Column(String(length=92), nullable=False)
    country = Column(String(length=48), nullable=False)

    location_zone = Column(Integer, ForeignKey('users.id'), nullable=False)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tg_username = Column(String(length=92), nullable=False, unique=True)
    tg_userid = Column(String(length=24), unique=True)
    pgo_username = Column(String(length=48), nullable=False)
    team = Column(String(length=24), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


def get_engine(url=None):
    url = url or 'sqlite:///:memory:'
    engine = create_engine(url, echo=True)
    Base.metadata.create_all(engine)


def get_session(engine):
    return sessionmaker(bind=engine)
