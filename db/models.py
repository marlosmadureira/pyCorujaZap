from sqlalchemy import (
    ForeignKeyConstraint, String, Text, TIMESTAMP, Boolean, ForeignKey, Integer, UniqueConstraint, Table, Column
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime


class Base(DeclarativeBase):
    pass


# Tabela de associação many-to-many entre operations e targets
operation_targets = Table(
    "operation_targets",
    Base.metadata,
    Column("operation_id", Integer, ForeignKey("operations.operation_id", ondelete="CASCADE"), primary_key=True),
    Column("target_id", Integer, ForeignKey("targets.target_id", ondelete="CASCADE"), primary_key=True)
)

# Tabela de associação many-to-many entre files e groups
file_groups = Table(
    "file_groups",
    Base.metadata,
    Column("file_id", Integer, ForeignKey("files.file_id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String(255), ForeignKey("whats_groups.group_id", ondelete="CASCADE"), primary_key=True)
)

# Tabela de associação many-to-many entre files e contacts
file_contacts = Table(
    "file_contacts",
    Base.metadata,
    Column("file_id", Integer, ForeignKey("files.file_id", ondelete="CASCADE"), primary_key=True),
    Column("contact_id", Integer, ForeignKey("contacts.contact_id", ondelete="CASCADE"), primary_key=True)
)


class Operation(Base):
    __tablename__ = 'operations'

    operation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")

    targets: Mapped[List["Target"]] = relationship("Target", secondary=operation_targets, back_populates="operations")


class Target(Base):
    __tablename__ = 'targets'

    target_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(String(255))
    external_id: Mapped[Optional[str]] = mapped_column(String(255))

    operations: Mapped[List["Operation"]] = relationship("Operation", secondary=operation_targets, back_populates="targets")
    

class File(Base):
    __tablename__ = 'files'

    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # FK COMPOSTA: operation_id + target_id referenciam operation_targets
    operation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    archive_name: Mapped[Optional[str]] = mapped_column(String(255))
    internal_ticket_number: Mapped[Optional[str]] = mapped_column(String(255))
    generated_timestamp: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    date_range_start: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    date_range_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
    process_status: Mapped[Optional[str]] = mapped_column(String(255))
    file_type: Mapped[Optional[str]] = mapped_column(String(255))

    # CONSTRAINT FK COMPOSTA - referencia operation_targets
    __table_args__ = (
        ForeignKeyConstraint(
            ['operation_id', 'target_id'],
            ['operation_targets.operation_id', 'operation_targets.target_id'],
            ondelete="CASCADE"
        ),
    )

    groups: Mapped[List["Group"]] = relationship("Group", secondary=file_groups, back_populates="files")
    contacts: Mapped[List["Contact"]] = relationship("Contact", secondary=file_contacts, back_populates="files")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="file", cascade="all, delete-orphan")


class Group(Base):
    __tablename__ = 'whats_groups'

    group_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    creation: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    __table_args__ = (
        UniqueConstraint('group_id', name='uq_group_id'),
    )

    files: Mapped[List["File"]] = relationship("File", secondary=file_groups, back_populates="groups")
    metadata_records: Mapped[List["GroupMetadata"]] = relationship("GroupMetadata", back_populates="group", cascade="all, delete-orphan")


class GroupMetadata(Base):
    __tablename__ = 'group_metadata'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[str] = mapped_column(String(255), ForeignKey('whats_groups.group_id', ondelete="CASCADE"), nullable=False)
    group_size: Mapped[Optional[int]] = mapped_column(Integer)
    subject: Mapped[Optional[str]] = mapped_column(Text)
    generated_timestamp: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    group: Mapped["Group"] = relationship("Group", back_populates="metadata_records")


class Contact(Base):
    __tablename__ = 'contacts'

    contact_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_phone: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_type: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint('contact_phone', 'contact_type', name='uq_contact_phone_type'),
    )

    files: Mapped[List["File"]] = relationship("File", secondary=file_contacts, back_populates="contacts")


class IP(Base):
    __tablename__ = 'ips'

    sender_ip: Mapped[str] = mapped_column(String(255), primary_key=True)
    continent: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(255))
    country_code: Mapped[Optional[str]] = mapped_column(String(255))
    region: Mapped[Optional[str]] = mapped_column(String(255))
    region_name: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(255))
    district: Mapped[Optional[str]] = mapped_column(String(255))
    zipcode_ip: Mapped[Optional[str]] = mapped_column(String(255))
    latitude: Mapped[Optional[str]] = mapped_column(String(255))
    longitude: Mapped[Optional[str]] = mapped_column(String(255))
    timezone_ip: Mapped[Optional[str]] = mapped_column(String(255))
    isp: Mapped[Optional[str]] = mapped_column(Text)
    org: Mapped[Optional[str]] = mapped_column(Text)
    as_name: Mapped[Optional[str]] = mapped_column(Text)
    mobile: Mapped[Optional[bool]] = mapped_column(Boolean)

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="ip")


class Message(Base):
    __tablename__ = 'messages'

    message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.file_id', ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    sender: Mapped[Optional[str]] = mapped_column(String(255))
    group_id: Mapped[Optional[str]] = mapped_column(String(255))
    sender_ip: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey('ips.sender_ip', ondelete='SET NULL'))
    sender_port: Mapped[Optional[str]] = mapped_column(String(255))
    sender_device: Mapped[Optional[str]] = mapped_column(String(255))
    message_type: Mapped[Optional[str]] = mapped_column(String(255))
    message_style: Mapped[Optional[str]] = mapped_column(String(255))
    message_size: Mapped[Optional[int]] = mapped_column(Integer)

    file: Mapped["File"] = relationship("File", back_populates="messages")
    ip: Mapped[Optional["IP"]] = relationship("IP", back_populates="messages")
    message_recipients: Mapped[List["MessageRecipient"]] = relationship("MessageRecipient", back_populates="message", cascade="all, delete-orphan")


class MessageRecipient(Base):
    __tablename__ = 'message_recipients'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(255), ForeignKey('messages.message_id', ondelete="CASCADE"), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(255), nullable=False)

    message: Mapped["Message"] = relationship("Message", back_populates="message_recipients")
