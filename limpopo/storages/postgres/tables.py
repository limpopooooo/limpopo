from sqlalchemy import (
    Boolean,
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import expression, func

from limpopo.dto import Messengers

metadata = MetaData()


respondents = Table(
    "respondents",
    metadata,
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("id", String, primary_key=True),
    Column("messenger", Enum(Messengers), primary_key=True),
    Column("username", String, nullable=True),
    Column("first_name", String, nullable=True),
    Column("last_name", String, nullable=True),
    Column("extra_data", JSONB, nullable=True),
)


dialogs = Table(
    "dialogs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("cancelled", Boolean, server_default=expression.false()),
    Column("completed", Boolean, server_default=expression.false()),
    Column("respondent_id", String, nullable=False),
    Column("respondent_messenger", Enum(Messengers), nullable=False),
    ForeignKeyConstraint(
        ["respondent_id", "respondent_messenger"],
        ["respondents.id", "respondents.messenger"],
    ),
)


dialogue_pauses = Table(
    "dialogue_pauses",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("dialog_id", Integer, ForeignKey(dialogs.c.id), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("active", Boolean, server_default=expression.true(), nullable=True),
    UniqueConstraint('dialog_id', 'active', name='one_pause_active')
)

called_functions = Table(
    "called_functions",
    metadata,
    Column("hash", BigInteger, primary_key=True),
    Column("dialog_id", Integer, ForeignKey(dialogs.c.id), primary_key=True),
)

dialogue_steps = Table(
    "dialogue_steps",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("dialog_id", Integer, ForeignKey(dialogs.c.id), nullable=False),
    Column("question", String, nullable=False),
    Column("answer", String, nullable=False),
)

Index(
    "idx_dialog_fk_respondent", dialogs.c.respondent_id, dialogs.c.respondent_messenger
)
Index("idx_dialogue_steps_fk_dialog", dialogue_steps.c.dialog_id)
