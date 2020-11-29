import logging
import asyncio

from telethon import TelegramClient, events
from telethon import Button
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer

from .. import const
from ..dto import Message, Messengers
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
                    rows_buttons.append(buttons[-(len(buttons) % question.column_count):])
                buttons = rows_buttons

            return {
                'message': message,
                'buttons': buttons
            }

        return {
            'message': message
        }

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

    def __init__(self, quiz, storage, settings, *args, **kwargs):
        super().__init__(quiz, storage, settings)
        self._bot = TelegramClient(
            "testbot",
            settings['api_id'],
            settings['api_hash'],
            proxy=None
        ).start(bot_token=settings['token'])

    async def handle_click_button(self, event):
        if event.chat_id not in self.dialogs:
            await self._bot.send_message(event.chat, const.FOREWORD)
            return

        dialog = self.dialogs[event.chat_id]

        message = Message(event.message_id, event.query.data.decode())
        await dialog.handle_message(message)

    async def handle_new_message(self, event):
        if event.chat_id not in self.dialogs:
            await self._bot.send_message(event.chat, const.FOREWORD)
            return

        dialog = self.dialogs[event.chat_id]

        message = Message(event.message.id, event.message.text)
        await dialog.handle_message(event.message)

    async def handle_start(self, event):
        """Start super!"""

        try:
            if event.chat_id in self.dialogs:
                await self.close_dialog(event.chat)

            dialog = await self.create_dialog(event.chat)
            await self.quiz(dialog)
        finally:
            await self.close_dialog(event.chat)
            raise events.StopPropagation

    async def handle_cancel(self, event):
        try:
            if event.chat_id not in self.dialogs:
                await self._bot.send_message(event.chat, const.SESSION_DOESNT_EXIST)
                return
                
            await self.close_dialog(event.chat)
            await self._bot.send_message(event.chat, const.CANCEL)
        finally:
            raise events.StopPropagation

    async def close_dialog(self, user):
        dialog = self.dialogs.pop(user.id, None)
        if dialog:
            await dialog.close()
            logging.info('Dialog {} was closed'.format(user.id))
        else:
            logging.info('Dialog {} doesn\'t found'.format(user.id))

    async def create_dialog(self, user):
        dialog = TelegramDialog(
            self,
            user.id,
            user.username,
            **self.settings.get('dialog', {})
        )

        await dialog.start()

        self.dialogs[user.id] = dialog

        logging.info('New dialog was created with id: {}'.format(user.id))

        return dialog

    async def send_message(self, user_id, *args, **kwargs):
        message = await self._bot.send_message(user_id, *args, **kwargs)
        return message.id

    def run_forever(self):
        self._bot.add_event_handler(self.handle_start, events.NewMessage(pattern="/start"))
        self._bot.add_event_handler(self.handle_cancel, events.NewMessage(pattern="/cancel"))
        self._bot.add_event_handler(self.handle_new_message, events.NewMessage)
        self._bot.add_event_handler(self.handle_click_button, events.CallbackQuery)
        self._bot.run_until_disconnected()
