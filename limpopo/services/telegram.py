import asyncio
import logging
import typing

from telethon import Button, TelegramClient, events

from .. import const
from ..dto import Message, Messengers, Respondent
from .archetype import ArchetypeDialog, ArchetypeService


class TelegramDialog(ArchetypeDialog):
    def prepare_question(self, question) -> dict:
        message = question.topic

        buttons = []

        if question.options:
            for index, text in enumerate(question.options, 1):
                if question.inline:
                    buttons.append(Button.inline(text, index))
                else:
                    buttons.append(Button.text(text, single_use=True))

            if len(buttons) > question.column_count:
                rows_buttons = list(zip(*(question.column_count * [iter(buttons)])))
                if len(buttons) % question.column_count:
                    rows_buttons.append(
                        buttons[-(len(buttons) % question.column_count) :]
                    )
                buttons = rows_buttons

            return {"message": message, "buttons": buttons}

        return {"message": message}

    def prepare_answer(self, question, answer):
        if question.options and question.inline:
            try:
                index = int(answer.text) - 1
                answer.text = question.options[index]
            except ValueError:
                pass

        return answer


class TelegramService(ArchetypeService):
    type = Messengers.telegram

    def __init__(
        self, quiz, storage, settings, cls_dialog=TelegramDialog, *args, **kwargs
    ):
        super().__init__(quiz, storage, settings, cls_dialog)
        self._bot = TelegramClient(
            "testbot", settings["api_id"], settings["api_hash"], proxy=None
        )
    async def restore_dialog(
        self, respondent_id, event
    ) -> typing.Optional[TelegramDialog]:

        last_dialog_id = await self.storage.get_last_dialog_id(
            respondent_id=respondent_id, respondent_messenger=self.type
        )

        if last_dialog_id is None:
            logging.info(
                "Respondent #{} doesn't have any dialogs".format(respondent_id)
            )
            return

        messages = await self.storage.get_messages_from_dialog(last_dialog_id)
        prepared_questions = {q: a for q, a in messages}

        respondent = Respondent(
            id=respondent_id,
            messenger=self.type,
            username=event.chat.username,
            first_name=event.chat.first_name,
            last_name=event.chat.last_name,
        )

        dialog = await self.create_dialog(
            respondent, identifier=last_dialog_id, prepared_questions=prepared_questions
        )

        asyncio.ensure_future(self.run_quiz(dialog))

        return dialog

    async def get_or_restore_dialog(self, event) -> typing.Optional[TelegramDialog]:
        respondent_id = str(event.chat_id)
        if respondent_id in self.dialogs:
            return self.dialogs[respondent_id]

        dialog = await self.restore_dialog(respondent_id, event)

        if dialog is None:
            await self._bot.send_message(event.chat_id, const.FOREWORD)
        else:
            return dialog

    async def handle_click_button(self, event):
        try:
            dialog = await self.get_or_restore_dialog(event)
            if dialog is None:
                return

            message = Message(event.message_id, event.query.data.decode())
            await dialog.handle_message(message)
        except Exception:
            logging.exception("Catch exception in handle_click_button:")
            raise

    async def handle_new_message(self, event):
        try:
            dialog = await self.get_or_restore_dialog(event)
            if dialog is None:
                return

            message = Message(event.message.id, event.message.text)
            await dialog.handle_message(message)
        except Exception:
            logging.exception("Catch exception in handle_new_message:")
            raise

    async def handle_start(self, event):
        try:
            respondent_id = str(event.chat_id)
            if respondent_id in self.dialogs:
                await self.close_dialog(respondent_id, is_complete=False)

            respondent = Respondent(
                id=respondent_id,
                messenger=self.type,
                username=event.chat.username,
                first_name=event.chat.first_name,
                last_name=event.chat.last_name,
            )

            dialog = await self.create_dialog(respondent)
            await self.run_quiz(dialog)
        except Exception:
            logging.exception("Catch exception in handle_start:")
            raise
        finally:
            raise events.StopPropagation

    async def handle_cancel(self, event):
        try:
            respondent_id = str(event.chat_id)

            if respondent_id not in self.dialogs:
                await self._bot.send_message(event.chat, const.SESSION_DOESNT_EXIST)
                return

            await self.close_dialog(respondent_id, is_complete=False)
            await self._bot.send_message(event.chat, const.CANCEL)
        except Exception:
            logging.exception("Catch exception in handle_cancel:")
        finally:
            raise events.StopPropagation

    async def send_message(self, user_id, *args, **kwargs):
        message = await self._bot.send_message(int(user_id), *args, **kwargs)
        return message.id

    def set_handlers(self):
        self._bot.add_event_handler(
            self.handle_start, events.NewMessage(pattern="/start")
        )
        self._bot.add_event_handler(
            self.handle_cancel, events.NewMessage(pattern="/cancel")
        )
        self._bot.add_event_handler(self.handle_new_message, events.NewMessage)
        self._bot.add_event_handler(self.handle_click_button, events.CallbackQuery)

    def run_forever(self):
        self.set_handlers()
        self._bot.start(bot_token=self.settings["token"])
        self._bot.run_until_disconnected()

    async def async_run_forever(self):
        self.set_handlers()
        await self._bot.start(bot_token=self.settings["token"])
        await self._bot.run_until_disconnected()
