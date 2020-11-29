from sqlalchemy import (
    Column,
    Enum,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
)

from ...dto import Messengers

metadata = MetaData()


dialogs = Table(
    "dialogs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("messenger", Enum(Messengers), primary_key=True),
    Column("username", String),
)


dialog_steps = Table(
    "dialog_steps",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("dialog_id", Integer),
    Column("messenger", Enum(Messengers)),
    Column("question", String),
    Column("answer", String),
    ForeignKeyConstraint(
        ["dialog_id", "messenger"], ["dialogs.id", "dialogs.messenger"]
    ),
)
