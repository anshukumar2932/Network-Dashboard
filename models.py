from typing import List, Optional
from sqlalchemy import create_engine, ForeignKey, String, Integer,BOOLEAN,Float,DateTime
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column, relationship
from datetime import datetime
from sqlalchemy.orm import sessionmaker

engine =create_engine('sqlite:///network.db',echo=True)

class Base(DeclarativeBase):
    pass

class Site(Base):
    __tablename__="sites"
    id : Mapped[int] =mapped_column(Integer, primary_key=True)
    location :Mapped[str] = mapped_column(String, nullable=False)
    sub_location :Mapped[str] = mapped_column(String, nullable=False)
    devices : Mapped[list["Device"]] = relationship(back_populates="site",cascade="all,delete-orphan")
    source_link: Mapped[list["Link"]] = relationship(foreign_keys="Link.source_site",back_populates="source")
    destination_link: Mapped[list["Link"]] = relationship(foreign_keys="Link.destination_site",back_populates="destination")
    def __repr__(self):
        return f"<Site {self.location}/{self.sub_location}>"

    
class Device(Base):
    __tablename__ = 'devices'
    id: Mapped[int]= mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"),nullable=False)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    ip: Mapped[str] = mapped_column(String,nullable=False,unique=True)
    status: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    last_seen: Mapped[datetime| None] = mapped_column(DateTime)
    site: Mapped["Site"] = relationship(back_populates="devices")
    ping_history: Mapped[list["PingHistory"]] = relationship(back_populates="device",cascade="all, delete-orphan")
    links_as_a: Mapped[list["Link"]] = relationship(
        foreign_keys="Link.device_a",
        back_populates="device_a_ref",
    )

    links_as_b: Mapped[list["Link"]] = relationship(
        foreign_keys="Link.device_b",
        back_populates="device_b_ref",
    )
    
class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source_site: Mapped[int] = mapped_column(
        ForeignKey("sites.id"),
        nullable=False,
    )

    destination_site: Mapped[int] = mapped_column(
        ForeignKey("sites.id"),
        nullable=False,
    )

    device_a: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id")
    )

    device_b: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id")
    )

    source: Mapped["Site"] = relationship(
        foreign_keys=[source_site],
        back_populates="source_link",
    )

    destination: Mapped["Site"] = relationship(
        foreign_keys=[destination_site],
        back_populates="destination_link",
    )

    device_a_ref: Mapped["Device | None"] = relationship(
        foreign_keys=[device_a],
        back_populates="links_as_a",
    )

    device_b_ref: Mapped["Device | None"] = relationship(
        foreign_keys=[device_b],
        back_populates="links_as_b",
    )


class PingHistory(Base):
    __tablename__ = "ping_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id")
    )

    ping_time: Mapped[datetime | None] = mapped_column(DateTime)

    latency_ms: Mapped[float | None] = mapped_column(Float)

    status: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)

    device: Mapped["Device | None"] = relationship(
        back_populates="ping_history"
    )

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    resolved: Mapped[bool] = mapped_column(
        BOOLEAN,
        default=False
    )





