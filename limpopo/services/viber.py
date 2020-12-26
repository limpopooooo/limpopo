import asyncio
import logging
import typing
from dataclasses import dataclass
from time import time

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from tenacity import RetryError
from uvicorn import Config, Server
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.event_type import EventType
from viberbot.api.messages import TextMessage, URLMessage

from .. import const
from ..dto import Message, Messengers, Respondent
from ..exceptions import SettingsError
from ..helpers import with_retry
from ..markdown_message import MarkdownMessage
from ..video import Video
from .archetype import ArchetypeDialog, ArchetypeService, DefaultSettings, EmptySettings


@dataclass
class _local_settings(EmptySettings):
    name: str
    token: str
    http_host: str
    http_port: int
    http_webhook_path: str = "/"
    avatar: str = const.LIMPOPO_AVATAR

    def __post_init__(self):
        if not isinstance(self.http_host, str):
            raise SettingsError(
                "ViberSettings field `http_host` must be of the str type"
            )

        if not isinstance(self.http_port, int):
            raise SettingsError(
                "ViberSettings field `http_port` must be of the int type"
            )

        if not isinstance(self.http_webhook_path, str):
            raise SettingsError(
                "ViberSettings field `http_webhook_path` must be of the str type"
            )
        elif not self.http_webhook_path.startswith("/"):
            raise SettingsError(
                "ViberSettings field `http_webhook_path` must start with '/'"
            )

        if not isinstance(self.name, str):
            raise SettingsError("ViberSettings field `name` must be of the str type")

        if not isinstance(self.token, str):
            raise SettingsError("ViberSettings field `token` must be of the str type")


@dataclass
class ViberSettings(DefaultSettings, _local_settings):
    pass


class ViberDialog(ArchetypeDialog):
    def prepare_question(self, question):
        message = question.plain_text

        if question.options:
            buttons = []
            columns = 6 / question.column_count
            column_in_last_row = len(question.options) % question.column_count
            last_row_from = len(question.options) - column_in_last_row
            for index, text in enumerate(question.options, 1):
                if index > last_row_from and column_in_last_row > 0:
                    columns = 6 / column_in_last_row
                buttons.append(
                    {
                        "Columns": columns,
                        "Rows": 1,
                        "BgColor": "#e6f5ff",
                        "ActionType": "reply",
                        "ActionBody": text,
                        "ReplyType": "message",
                        "Text": text,
                    }
                )

            keyboard = {
                "Type": "keyboard",
                "InputFieldState": "hidden" if question.strict_choose else "regular",
                "Buttons": buttons,
            }

            return TextMessage(text=message, keyboard=keyboard)

        return TextMessage(text=message)

    def prepare_answer(self, question, answer):
        return answer


class ViberService(ArchetypeService):
    type = Messengers.viber

    def __init__(
        self,
        quiz,
        storage,
        settings: ViberSettings,
        cls_dialog=ViberDialog,
        *args,
        **kwargs
    ):
        super().__init__(quiz, storage, settings, cls_dialog=cls_dialog)

        self._viber = Api(
            BotConfiguration(
                name=settings.name, avatar=settings.avatar, auth_token=settings.token
            )
        )

        self.app = Starlette(
            routes=[
                Route(
                    settings.http_webhook_path,
                    endpoint=self.handle_http_request,
                    methods=["POST", "GET"],
                )
            ]
        )
        config = Config(self.app, port=settings.http_port, host=settings.http_host)
        self._server = Server(config=config)

        self._keyboard_data = None

    @staticmethod
    def gen_tracking_data():
        return int(time() * 10 ** 5)

    @staticmethod
    def user_to_dict(user) -> dict:
        return {
            "name": user.name,
            "avatar": user.avatar,
            "id": user.id,
            "country": user.country,
            "language": user.language,
            "api_version": user.api_version,
        }

    def expand_tracking_data(self, message) -> None:
        tracking_data = self.gen_tracking_data()
        message._tracking_data = tracking_data

    def expand_keyboard(self, message) -> None:
        if self._keyboard_data is None:
            logging.warning(
                "Can't add keyboard to the message, because there are no keyboard"
            )
            return

        message._keyboard = self._keyboard_data

    def _create_task(self, dialog):
        asyncio.ensure_future(self.run_quiz(dialog))

    async def handle_http_request(self, request):
        body = await request.body()
        signature = request.headers.get("X-Viber-Content-Signature")

        if not self._viber.verify_signature(body, signature):
            return Response(status_code=403)

        viber_request = self._viber.parse_request(body)

        await self.handle_viber_request(viber_request)

        return Response(status_code=200)

    async def handle_viber_request(self, viber_request):
        logging.info(
            "Received viber_request with event_type {}".format(viber_request.event_type)
        )

        if viber_request.event_type == EventType.CONVERSATION_STARTED:
            return await self.handle_conversation_started(viber_request.user)
        elif viber_request.event_type == EventType.SUBSCRIBED:
            return await self.handle_subscribed(viber_request.user)
        elif viber_request.event_type == EventType.UNSUBSCRIBED:
            return await self.handle_unsubscribed(viber_request.user_id)
        elif viber_request.event_type == EventType.MESSAGE:
            return await self.handle_new_message(
                viber_request.sender, viber_request.message
            )

    async def handle_conversation_started(self, user):
        message = TextMessage(**const.VIBER_INTO_MESSAGE)
        self._viber.send_messages(user.id, message)

    async def handle_subscribed(self, user):
        full_userdata = self.user_to_dict(user)

        respondent = Respondent(
            id=user.id,
            messenger=self.type,
            username=user.name,
            extra_data=full_userdata,
        )

        dialog = await self.create_dialog(respondent)
        self._create_task(dialog)

    async def handle_new_message(self, user, message):
        message_text = message.text.strip()

        if message_text == self.settings.start_command:
            await self.handle_unsubscribed(user.id)
            await self.handle_subscribed(user)
            return
        elif message_text == self.settings.cancel_command:
            await self.handle_unsubscribed(user.id)
            return

        if message.tracking_data is None:
            logging.info("Received messageg without tracking_data")
            return

        dialog = await self.get_or_restore_dialog(user)

        if dialog:
            identifier = int(message.tracking_data) + 1
            message = Message(identifier, message_text)
            await dialog.handle_message(message)

    async def handle_unsubscribed(self, user_id):
        await self.close_dialog(user_id, is_complete=False)

    async def send_message(
        self, user_id, message, keep_keyboard=False, *args, **kwargs
    ):
        if isinstance(message, MarkdownMessage):
            message = TextMessage(text=message.plain_text)
        elif isinstance(message, Video):
            if message.url is not None:
                message = URLMessage(media=message.url)
            else:
                return self.gen_tracking_data()
        elif isinstance(message, str):
            message = TextMessage(text=message)

        if message._keyboard:
            self._keyboard_data = message._keyboard

        self.expand_tracking_data(message)

        if keep_keyboard:
            self.expand_keyboard(message)

        self._viber.send_messages(user_id, message)

        return message.tracking_data

    async def get_or_restore_dialog(self, user):
        if user.id in self.dialogs:
            return self.dialogs[user.id]

        dialog = await self.restore_dialog(user)

        if dialog is None and self.settings.reply_without_dialogue:
            foreword_message = const.FOREWORD.format(
                start_command=self.settings.start_command
            )
            await self.send_message(user.id, foreword_message)
        else:
            return dialog

    async def restore_dialog(self, user) -> typing.Optional[ViberDialog]:
        logging.debug("Try to restore dialog for user with id #{}".format(user.id))

        try:
            last_dialog_id = await with_retry(
                lambda: self.storage.get_last_dialog_id(
                    respondent_id=user.id, respondent_messenger=self.type
                ),
                exceptions=self.storage.io_exceptions,
                stop_callback_coro=self.stop,
            )

            if last_dialog_id is None:
                logging.info("Respondent #{} doesn't have any dialogs".format(user.id))
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

        full_userdata = self.user_to_dict(user)

        respondent = Respondent(
            id=user.id,
            messenger=self.type,
            username=user.name,
            extra_data=full_userdata,
        )

        dialog = await self.create_dialog(
            respondent, identifier=last_dialog_id, prepared_questions=prepared_questions
        )

        self._create_task(dialog)

        return dialog

    def set_webhook(self, url):
        events = self._viber.set_webhook(
            url,
            [
                EventType.MESSAGE,
                EventType.SUBSCRIBED,
                EventType.FAILED,
                EventType.CONVERSATION_STARTED,
            ],
        )

        logging.info(
            "ViberService has successfully signed up for the events: {}".format(events)
        )

    def unset_webhook(self):
        self._viber.unset_webhook()

    async def run_forever(self):
        await self._server.serve()

    async def stop(self):
        self._server.should_exit = True
        self._server.force_exit = True
