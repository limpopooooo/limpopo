import asyncio
import logging
import typing
from dataclasses import dataclass

from tenacity import RetryError
from telethon import Button, TelegramClient, events
from telethon.sessions.abstract import Session
from telethon.tl.types import DocumentAttributeVideo

from .. import const
from ..video import Video
from ..markdown_message import MarkdownMessage
from ..dto import Message, Messengers, Respondent
from ..exceptions import SettingsError
from ..helpers import with_retry
from ..storages.archetype import ArchetypeStorage
from .archetype import ArchetypeDialog, ArchetypeService, EmptySettings, DefaultSettings


@dataclass
class _local_settings(EmptySettings):
    api_id: int
    api_hash: str
    token: str
    session: typing.Union[str, Session] = "default_session"

    def __post_init__(self):
        if not isinstance(self.api_id, int):
            raise SettingsError(
                "TelegramSettings field `api_id` must be of the int type"
            )

        if not isinstance(self.api_hash, str):
            raise SettingsError(
                "TelegramSettings field `api_hash` must be of the str type"
            )

        if not isinstance(self.token, str):
            raise SettingsError(
                "TelegramSettings field `token` must be of the str type"
            )

        if not (isinstance(self.session, str) or isinstance(self.session, Session)):
            raise SettingsError(
                "TelegramSettings field `` must be of the str type or Session instance"
            )


@dataclass
class TelegramSettings(DefaultSettings, _local_settings):
    pass


class TelegramDialog(ArchetypeDialog):
    def prepare_question(self, question) -> dict:
        message = question.topic

        buttons = []

        if question.options:
            for index, text in enumerate(question.options, 1):
                if question.inline:
                    buttons.append(Button.inline(text, index))
                else:
                    buttons.append(Button.text(text, single_use=True, resize=True))

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
        self,
        quiz: typing.Callable[[TelegramDialog], None],
        storage: ArchetypeStorage,
        settings: TelegramSettings,
        cls_dialog: TelegramDialog = TelegramDialog,
        *args,
        **kwargs
    ):
        super().__init__(quiz, storage, settings, cls_dialog)
        self._client = TelegramClient(
            settings.session, settings.api_id, settings.api_hash, proxy=None
        )
        self._uploaded_file = None

    async def upload_file(self, video_file):
        if self._uploaded_file is None:
            self._uploaded_file = await self._client.upload_file(video_file)

        return self._uploaded_file

    async def restore_dialog(
        self, respondent_id, event, repeat_last_question=False
    ) -> typing.Optional[TelegramDialog]:

        try:
            last_dialog_id = await with_retry(
                lambda: self.storage.get_last_dialog_id(
                    respondent_id=respondent_id, respondent_messenger=self.type
                ),
                exceptions=self.storage.io_exceptions,
                stop_callback_coro=self.stop,
            )

            if last_dialog_id is None:
                logging.info(
                    "Respondent #{} doesn't have any dialogs".format(respondent_id)
                )
                return

            messages = await with_retry(
                lambda: self.storage.get_messages_from_dialog(last_dialog_id),
                exceptions=self.storage.io_exceptions,
                stop_callback_coro=self.stop,
            )
        except RetryError:
            logging.error("Can't restore dialog due to Storage IO error")
            return

        prepared_questions = {q: a for q, a in messages}

        respondent = Respondent(
            id=respondent_id,
            messenger=self.type,
            username=event.chat.username,
            first_name=event.chat.first_name,
            last_name=event.chat.last_name,
        )

        dialog = await self.create_dialog(
            respondent,
            identifier=last_dialog_id,
            prepared_questions=prepared_questions,
            repeat_last_question=repeat_last_question,
        )

        asyncio.ensure_future(self.run_quiz(dialog))

        return dialog

    async def get_or_restore_dialog(self, event) -> typing.Optional[TelegramDialog]:
        respondent_id = str(event.chat_id)
        if respondent_id in self.dialogs:
            return self.dialogs[respondent_id]

        dialog = await self.restore_dialog(respondent_id, event)

        if dialog is None and self.settings.reply_without_dialogue:
            foreword_message = const.FOREWORD.format(
                start_command=self.settings.start_command
            )
            await self._client.send_message(event.chat_id, foreword_message)
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

    async def cancel_pause(self, respondent_id):
        try:
            last_dialog_id = await with_retry(
                lambda: self.storage.get_last_dialog_id(
                    respondent_id=respondent_id,
                    respondent_messenger=self.type,
                    on_pause=True,
                ),
                exceptions=self.storage.io_exceptions,
                stop_callback_coro=self.stop,
            )

            if last_dialog_id is None:
                logging.info(
                    "Respondent #{} doesn't have dialog on pause".format(respondent_id)
                )
                return

            return await with_retry(
                lambda: self.storage.cancel_pause(last_dialog_id),
                exceptions=self.storage.io_exceptions,
                stop_callback_coro=self.stop,
            )

        except RetryError:
            logging.error("Can't restore dialog on pause due to Storage IO error")
            return

    async def handle_start(self, event):
        try:
            logging.info("Handle start command respondent #{}".format(event.chat_id))

            respondent_id = str(event.chat_id)

            dialog = await self.get_or_restore_dialog(event)

            if dialog:
                logging.info(
                    "Respondent #{} try to start already started dialog".format(
                        respondent_id
                    )
                )
                return

            cancelled = await self.cancel_pause(respondent_id)

            if cancelled:
                await self.send_message(respondent_id, const.PAUSE_CANCELLED)

                await self.restore_dialog(
                    respondent_id, event, repeat_last_question=True
                )
            else:
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

    async def handle_pause(self, event):
        try:
            logging.info("Handle pause command respondent #{}".format(event.chat_id))

            dialog = await self.get_or_restore_dialog(event)

            if dialog is None:
                logging.warning(
                    "Can't set pause to dialogue with respondent #{}, dialog doesn't found".format(
                        event.chat_id
                    )
                )
                return

            await self.close_dialog(dialog.respondent.id, is_complete=None)
            await dialog.pause()
            await self.send_message(dialog.respondent.id, const.DIALOG_ON_PAUSE)

        except Exception:
            logging.exception("Catch exception in handle_pause:")
            raise
        finally:
            raise events.StopPropagation

    async def handle_cancel(self, event):
        try:
            dialog = await self.get_or_restore_dialog(event)

            if dialog is None:
                await self._client.send_message(event.chat, const.SESSION_DOESNT_EXIST)
                return

            await self.close_dialog(dialog.respondent.id, is_complete=False)

            cancel_message = const.CANCEL.format(
                start_command=self.settings.start_command
            )
            await self._client.send_message(event.chat, cancel_message)
        except Exception:
            logging.exception("Catch exception in handle_cancel:")
        finally:
            raise events.StopPropagation

    async def send_message(
        self, user_id, message, keep_keyboard=False, *args, **kwargs
    ):
        if isinstance(message, MarkdownMessage):
            message = {"message": message.text}

            if not keep_keyboard:
                message["buttons"] = Button.clear()

            message = await self._client.send_message(int(user_id), **message)

        elif isinstance(message, Video):
            if message.width and message.height:
                attrs = DocumentAttributeVideo(
                    0, message.width, message.height, supports_streaming=True
                )
            else:
                attrs = DocumentAttributeVideo(0, 0, 0, supports_streaming=True)

            uploaded_file = await self.upload_file(message.path_to_file)

            message = await self._client.send_file(
                int(user_id), uploaded_file, attributes=(attrs,)
            )

        elif isinstance(message, dict):
            message = await self._client.send_message(int(user_id), **message)

        elif isinstance(message, str):
            message = {"message": message}

            if not keep_keyboard:
                message["buttons"] = Button.clear()

            message = await self._client.send_message(int(user_id), **message)

        return message.id

    def set_handlers(self):
        self._client.add_event_handler(
            self.handle_start, events.NewMessage(pattern=self.settings.start_command)
        )
        self._client.add_event_handler(
            self.handle_pause, events.NewMessage(pattern=self.settings.pause_command)
        )
        self._client.add_event_handler(
            self.handle_cancel, events.NewMessage(pattern=self.settings.cancel_command)
        )
        self._client.add_event_handler(self.handle_new_message, events.NewMessage)
        self._client.add_event_handler(self.handle_click_button, events.CallbackQuery)

    async def stop(self):
        await self._client.disconnect()

    async def run_forever(self):
        self.set_handlers()
        await self._client.start(bot_token=self.settings.token)
        await self._client.run_until_disconnected()
