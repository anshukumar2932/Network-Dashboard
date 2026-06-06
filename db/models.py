from typing import List, Optional
from sqlalchemy import create_engine, ForeignKey, String, Integer,BOOLEAN,Float,DateTime, delete,Enum,event
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column, relationship
from datetime import datetime

engine =create_engine('sqlite:///network.db',echo=True)
@engine.listens_for(engine,"connect")
def set_sqlite_pragma(dbapi_connection,connection_record):
    cursor=dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class Base(DeclarativeBase):
    pass

class Location(Base):
    __tablename__="locations"
    id: Mapped[int] =mapped_column(Integer, primary_key=True)
    name: Mapped[str] =mapped_column(String, nullable=False, unique=True)
    sites: Mapped[list["Site"]] = relationship("Site", back_populates="location",cascade="all,delete-orphan")

class Site(Base):
    __tablename__="sites"
    id : Mapped[int] =mapped_column(Integer, primary_key=True)
    location_id :Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    name :Mapped[str] = mapped_column(String, nullable=False)
    devices : Mapped[list["Device"]] = relationship(back_populates="site",cascade="all,delete-orphan")
    source_link: Mapped[list["Link"]] = relationship(foreign_keys="Link.source_site",back_populates="source")
    destination_link: Mapped[list["Link"]] = relationship(foreign_keys="Link.destination_site",back_populates="destination")
    location: Mapped["Location"]=relationship(back_populates="sites")
    def __repr__(self):
        return f"<Site {self.location.name} name={self.name}>"
 
    
class Device(Base):
    __tablename__ = 'devices'
    id: Mapped[int]= mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"),nullable=False)
    hostname: Mapped[str] = mapped_column(String, nullable=False,unique=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    ip: Mapped[str] = mapped_column(String,nullable=False,unique=True)
    category: Mapped[str] =mapped_column(Enum("radio","ap","switch","router","server",name="device_category"),nullable=False)
    status: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    last_seen: Mapped[datetime| None] = mapped_column(DateTime)
    site: Mapped["Site"] = relationship(back_populates="devices")
    ping_history: Mapped[list["PingHistory"]] = relationship(back_populates="device",cascade="all, delete-orphan")
    links_a: Mapped[list["Link"]] = relationship(foreign_keys="Link.device_a",back_populates="device_a_ref")
    links_b: Mapped[list["Link"]] = relationship(foreign_keys="Link.device_b",back_populates="device_b_ref",)
    
class Link(Base):
    __tablename__ = "links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_site: Mapped[int] = mapped_column(ForeignKey("sites.id"),nullable=False,)
    destination_site: Mapped[int] = mapped_column(ForeignKey("sites.id"),nullable=False)
    device_a: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    device_b: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    source: Mapped["Site"] = relationship(foreign_keys=[source_site],back_populates="source_link")
    destination: Mapped["Site"] = relationship(foreign_keys=[destination_site],back_populates="destination_link")
    device_a_ref: Mapped["Device | None"] = relationship(foreign_keys=[device_a],back_populates="links_a")
    device_b_ref: Mapped["Device | None"] = relationship(foreign_keys=[device_b],back_populates="links_b")
    status: Mapped[bool] = mapped_column(BOOLEAN,default=True,nullable=False)
    last_checked: Mapped[datetime|None] = mapped_column(DateTime)


class PingHistory(Base):
    __tablename__ = "ping_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    ping_time: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    status: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    device: Mapped["Device"] = relationship(back_populates="ping_history")

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    link_id: Mapped[int | None] = mapped_column(ForeignKey("links.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(BOOLEAN,default=False)

class User(Base):
    __tablename__="users"
    id: Mapped[int] =mapped_column(primary_key=True)
    user: Mapped[str] =mapped_column(String,nullable=False,unique=True)
    passwd: Mapped[str] = mapped_column(String,nullable=False)



