from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import dialect, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import func, null

from ..archetype import ArchetypeStorage
from . import tables


class PostgreStorage(ArchetypeStorage):
    io_exceptions = (ConnectionRefusedError, SQLAlchemyError)

    def __init__(self, uri):
        self._engine = create_async_engine(uri)

    async def save_question_and_answer(self, dialog, question):
        async with self._engine.begin() as conn:
            await conn.execute(
                tables.dialogue_steps.insert().values(
                    {
                        "dialog_id": dialog.id,
                        "question": question.plain_text,
                        "answer": dialog.answer.text,
                    }
                )
            )

    async def save_function_call(self, dialog, funcs_hash: int):
        async with self._engine.begin() as conn:
            await conn.execute(
                tables.called_functions.insert().values(
                    {"hash": funcs_hash, "dialog_id": dialog.id}
                )
            )

    async def create_respondent_if_not_exists(self, respondent, conn=None):
        values = {
            "id": respondent.id,
            "messenger": respondent.messenger,
            "username": respondent.username,
            "first_name": respondent.first_name,
            "last_name": respondent.last_name,
            "extra_data": respondent.extra_data,
        }
        values = {k: v for k, v in values.items() if v is not None}
        set_on_conflict = values.copy()
        set_on_conflict.pop("id")
        set_on_conflict.pop("messenger")

        insert_stmt = insert(tables.respondents).values(**values)
        do_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[tables.respondents.c.id, tables.respondents.c.messenger],
            set_=set_on_conflict,
        )

        if conn:
            await conn.execute(do_update_stmt)
        else:
            async with self._engine.begin() as conn:
                await conn.execute(do_update_stmt)

    async def create_dialog(self, dialog) -> int:
        async with self._engine.begin() as conn:
            await self.create_respondent_if_not_exists(dialog.respondent, conn=conn)

            result = await conn.execute(
                tables.dialogs.insert().values(
                    {
                        "respondent_id": dialog.respondent.id,
                        "respondent_messenger": dialog.respondent.messenger,
                    }
                )
            )

            return result.inserted_primary_key[0]

    async def get_last_dialog_id(
        self, respondent_id, respondent_messenger, on_pause=None
    ):

        if on_pause is None:
            on_pause = null()

        async with self._engine.begin() as conn:
            query = text(
                """
                SELECT
                    MAX(d.id)
                FROM dialogs as d
                LEFT OUTER JOIN dialogue_pauses as dp ON dp.dialog_id = d.id AND dp.active=True
                WHERE
                    d.respondent_id = :id
                    AND d.respondent_messenger = :messenger
                    AND d.finished_at is Null
                    AND dp.active is :on_pause;
            """
            )

            stmt = query.bindparams(
                **{
                    "id": respondent_id,
                    "messenger": respondent_messenger.name,
                    "on_pause": on_pause,
                }
            )

            stmt_compiled = stmt.compile(
                dialect=dialect(), compile_kwargs={"literal_binds": True}
            )
            result = await conn.execute(stmt_compiled)
            data = result.fetchone()

            if data:
                return data[0]

    async def get_messages_from_dialog(self, dialog_id: int):
        async with self._engine.begin() as conn:
            result = await conn.execute(
                select(
                    [tables.dialogue_steps.c.question, tables.dialogue_steps.c.answer]
                )
                .where(tables.dialogue_steps.c.dialog_id == dialog_id)
                .order_by(tables.dialogue_steps.c.created_at)
            )

            return result.fetchall()

    async def get_called_functions_from_dialog(self, dialog_id: int):
        async with self._engine.begin() as conn:
            result = await conn.execute(
                select(
                    [tables.called_functions.c.hash]
                )
                .where(tables.called_functions.c.dialog_id == dialog_id)
                .order_by(tables.called_functions.c.created_at)
            )

            return result.fetchall()

    async def close_dialog(self, dialog, is_complete):
        values = {"finished_at": func.now()}

        if is_complete:
            values["completed"] = True
        else:
            values["cancelled"] = True

        async with self._engine.begin() as conn:
            await conn.execute(
                tables.dialogs.update()
                .values(values)
                .where(tables.dialogs.c.id == dialog.id)
            )

    async def pause(self, dialog):
        async with self._engine.begin() as conn:
            try:
                await conn.execute(
                    tables.dialogue_pauses.insert().values(
                        {
                            "dialog_id": dialog.id,
                        }
                    )
                )
            except IndentationError:
                return False

            return True

    async def cancel_pause(self, dialog_id) -> bool:
        async with self._engine.begin() as conn:
            values = {"finished_at": func.now(), "active": null()}

            result = await conn.execute(
                tables.dialogue_pauses.update()
                .values(values)
                .where(tables.dialogue_pauses.c.dialog_id == dialog_id)
                .where(tables.dialogue_pauses.c.active.is_(True))
            )

            return bool(result.rowcount)
