from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, create_engine, Sequence, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Group(Base):
    __tablename__ = 'group'

    id = Column(Integer, Sequence('group_id_seq'), primary_key=True)
    tg_chat_id = Column(String(length=24), unique=True, nullable=False)
    tg_chat_name = Column(String(length=92), nullable=True)
    search_filter = Column(Text, default='{}')


class LocationZone(Base):
    __tablename__ = 'location_zones'
    
    id = Column(Integer, Sequence('location_id_seq'), primary_key=True)
    suburb = Column(String(length=128), nullable=True)
    town = Column(String(length=92), nullable=True)
    city_district = Column(String(length=92), nullable=True)
    city = Column(String(length=92), nullable=True)
    county = Column(String(length=92), nullable=True)
    state = Column(String(length=92), nullable=True)
    country = Column(String(length=48), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates='location_zones')

    def __str__(self):
        return ' '.join(list(filter(lambda x: x, [self.suburb, self.town, self.city_district, self.city, self.county,
                                    self.state, self.country])))


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    tg_username = Column(String(length=92), nullable=False)
    tg_userid = Column(String(length=24), unique=True)
    pgo_username = Column(String(length=48), nullable=False)
    team = Column(String(length=24), nullable=True)
    notifications = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

User.location_zones = relationship("LocationZone", order_by=LocationZone.id, back_populates="user")


def get_engine(url=None):
    url = url or 'sqlite:///:memory:'
    engine = create_engine(url, echo=True)
    Base.metadata.create_all(engine)
    return engine


def get_sessionmaker(engine):
    return sessionmaker(bind=engine)
