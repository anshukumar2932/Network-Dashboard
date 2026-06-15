import os
from dotenv import load_dotenv
load_dotenv()
from typing import List, Optional
from sqlalchemy import create_engine, ForeignKey, String, Integer, Boolean, Float, DateTime, Text, event, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_login import UserMixin
from datetime import datetime, timezone

engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///network.db"), echo=False)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    devices: Mapped[list["Device"]] = relationship(back_populates="category_obj")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_device_status", "status"),
        Index("idx_device_location", "location"),
        Index("idx_device_ip", "ip"),
        Index("idx_device_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    hostname: Mapped[str] = mapped_column(String(100), default="")
    device_name: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id"),
        nullable=False,
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    category_obj: Mapped["Category"] = relationship(back_populates="devices")
    ping_history: Mapped[list["PingHistory"]] = relationship(
        foreign_keys="PingHistory.device_ip",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    source_links: Mapped[list["NetworkLink"]] = relationship(
        foreign_keys="NetworkLink.source_ip",
        back_populates="source_device",
        cascade="all, delete-orphan",
    )
    destination_links: Mapped[list["NetworkLink"]] = relationship(
        foreign_keys="NetworkLink.destination_ip",
        back_populates="destination_device",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        foreign_keys="Alert.device_ip",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class NetworkLink(Base):
    __tablename__ = "network_links"
    __table_args__ = (
        Index("idx_link_source", "source_ip"),
        Index("idx_link_destination", "destination_ip"),
        Index("idx_link_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ip: Mapped[str] = mapped_column(
        ForeignKey("devices.ip", ondelete="CASCADE"),
        nullable=False,
    )
    destination_ip: Mapped[str | None] = mapped_column(
        ForeignKey("devices.ip", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), default="")
    bandwidth: Mapped[str] = mapped_column(String(50), default="")
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    source_device: Mapped["Device"] = relationship(
        foreign_keys=[source_ip], back_populates="source_links"
    )
    destination_device: Mapped["Device"] = relationship(
        foreign_keys=[destination_ip], back_populates="destination_links"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        foreign_keys="Alert.link_id",
        back_populates="link",
        cascade="all, delete-orphan",
    )


class PingHistory(Base):
    __tablename__ = "ping_history"
    __table_args__ = (
        Index("idx_ping_device", "device_ip"),
        Index("idx_ping_time", "ping_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_ip: Mapped[str] = mapped_column(
        ForeignKey("devices.ip", ondelete="CASCADE"),
        nullable=False,
    )
    ping_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    device: Mapped["Device"] = relationship(
        foreign_keys=[device_ip], back_populates="ping_history"
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_ip: Mapped[str] = mapped_column(
        ForeignKey("devices.ip", ondelete="CASCADE"),
        nullable=False,
    )
    link_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_links.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    device: Mapped["Device"] = relationship(
        foreign_keys=[device_ip], back_populates="alerts"
    )
    link: Mapped["NetworkLink"] = relationship(
        foreign_keys=[link_id], back_populates="alerts"
    )


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    passwd: Mapped[str] = mapped_column(String, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)


class TopologyCache(Base):
    __tablename__ = "topology_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    data: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class DashboardState(Base):
    __tablename__ = "dashboard_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zoom: Mapped[float] = mapped_column(Float, default=1.0)
    pan_x: Mapped[float] = mapped_column(Float, default=0.0)
    pan_y: Mapped[float] = mapped_column(Float, default=0.0)
    collapsed: Mapped[str] = mapped_column(Text, default="[]")
    node_positions: Mapped[str] = mapped_column(Text, default="{}")
    layout_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
