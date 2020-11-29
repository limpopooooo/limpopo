from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from ..archetype import ArchetypeStorage
from . import tables


class PostgreStorage(ArchetypeStorage):
    def __init__(self, uri):
        self._engine = create_async_engine(uri)

    async def save_question_and_answer(self, dialog, question):
        async with self._engine.begin() as conn:
            await conn.execute(
                tables.dialog_steps.insert().values({
                    'dialog_id': dialog.identifier,
                    'messenger': dialog.service.type,
                    'question': question.topic,
                    'answer': dialog.answer.text
                     })
            )

    async def save_dialog(self, dialog):
        async with self._engine.begin() as conn:
            try:
                await conn.execute(
                    tables.dialogs.insert().values({
                        'id': dialog.identifier,
                        'messenger': dialog.service.type,
                        'username': dialog.username,
                        })
                )
            except IntegrityError:
                pass
