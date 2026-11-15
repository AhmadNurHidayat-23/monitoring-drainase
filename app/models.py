from sqlalchemy import Column,Integer,String,Float,ForeignKey,CheckConstraint
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True)
    username=Column(String,nullable=False,unique=True)
    name=Column(String,nullable=False)
    role=Column(String,nullable=False)
    password=Column(String,nullable=False)
    active=Column(Integer,nullable=False,default=1)

class Region(Base):
    __tablename__='regions'
    id=Column(Integer,primary_key=True)
    name=Column(String,nullable=False,unique=True)

class Channel(Base):
    __tablename__='channels'
    id=Column(Integer,primary_key=True)
    code=Column(String(collation='NOCASE'),nullable=False,unique=True)
    name=Column(String,nullable=False)
    address=Column(String,nullable=False)
    region_id=Column(Integer,ForeignKey('regions.id'),nullable=False)
    length=Column(Float,nullable=False)
    kind=Column(String,nullable=False)
    lat=Column(Float,nullable=False)
    lng=Column(Float,nullable=False)
    staff_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    archived=Column(Integer,nullable=False,default=0)
    __table_args__=(CheckConstraint('length>0 AND lat BETWEEN -90 AND 90 AND lng BETWEEN -180 AND 180'),)

class InspectionPlan(Base):
    __tablename__='inspection_plans'
    id=Column(Integer,primary_key=True)
    channel_id=Column(Integer,ForeignKey('channels.id'),nullable=False)
    staff_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    on_date=Column(String,nullable=False)
    note=Column(String,nullable=False)
    canceled=Column(Integer,nullable=False,default=0)

class Inspection(Base):
    __tablename__='inspections'
    id=Column(Integer,primary_key=True)
    channel_id=Column(Integer,ForeignKey('channels.id'),nullable=False)
    plan_id=Column(Integer,ForeignKey('inspection_plans.id'),unique=True)
    on_date=Column(String,nullable=False)
    damage=Column(Integer,nullable=False)
    blockage=Column(Integer,nullable=False)
    condition=Column(String,nullable=False)
    blockage_note=Column(String,nullable=False)
    note=Column(String,nullable=False)
    actor_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    __table_args__=(CheckConstraint('damage BETWEEN 0 AND 3 AND blockage BETWEEN 0 AND 100'),)

class Job(Base):
    __tablename__='jobs'
    id=Column(Integer,primary_key=True)
    channel_id=Column(Integer,ForeignKey('channels.id'),nullable=False)
    staff_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    starts_on=Column(String,nullable=False)
    target_on=Column(String,nullable=False)
    task=Column(String,nullable=False)
    version=Column(Integer,nullable=False,default=1)
    canceled=Column(Integer,nullable=False,default=0)
    __table_args__=(CheckConstraint('target_on>=starts_on'),)

class Work(Base):
    __tablename__='works'
    id=Column(Integer,primary_key=True)
    job_id=Column(Integer,ForeignKey('jobs.id'),nullable=False)
    on_date=Column(String,nullable=False)
    status=Column(String,nullable=False)
    progress=Column(Integer,nullable=False)
    note=Column(String,nullable=False)
    actor_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    __table_args__=(CheckConstraint('progress BETWEEN 0 AND 100'),)

class Photo(Base):
    __tablename__='photos'
    id=Column(Integer,primary_key=True)
    inspection_id=Column(Integer,ForeignKey('inspections.id'))
    work_id=Column(Integer,ForeignKey('works.id'))
    token=Column(String,nullable=False,unique=True)
    stage=Column(String,nullable=False)
    caption=Column(String,nullable=False)
    actor_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    __table_args__=(CheckConstraint('(inspection_id IS NULL)<>(work_id IS NULL)'),)
