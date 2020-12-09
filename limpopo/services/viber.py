import asyncio
import logging
from time import time

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from uvicorn import Config, Server
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.event_type import EventType
from viberbot.api.messages import TextMessage

from ..const import LIMPOPO_AVATAR
from ..dto import Message, Messengers, Respondent
from .archetype import ArchetypeDialog, ArchetypeService


class ViberDialog(ArchetypeDialog):
    def prepare_question(self, question):
        message = question.topic
        tracking_data = int(time() * 10 ** 5)

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

            print(keyboard)

            return TextMessage(
                text=message, keyboard=keyboard, tracking_data=tracking_data
            )

        return TextMessage(text=message, tracking_data=tracking_data)

    def prepare_answer(self, question, answer):
        return answer


class ViberService(ArchetypeService):
    type = Messengers.viber

    def __init__(
        self, quiz, storage, settings, cls_dialog=ViberDialog, *args, **kwargs
    ):
        super().__init__(quiz, storage, settings, cls_dialog=cls_dialog)

        self._viber = Api(
            BotConfiguration(
                name=settings["viber_name"],
                avatar=settings.get("viber_avatar", LIMPOPO_AVATAR),
                auth_token=settings["viber_token"],
            )
        )

        self.app = Starlette(
            routes=[
                Route("/", endpoint=self.handle_http_request, methods=["POST", "GET"])
            ]
        )
        config = Config(
            self.app, port=self.settings["port"], host=self.settings["host"]
        )
        self._server = Server(config=config)
        self._tasks = {}

    async def handle_http_request(self, request):
        body = await request.body()
        signature = request.headers.get("X-Viber-Content-Signature")

        if not self._viber.verify_signature(body, signature):
            return Response(status_code=403)

        viber_request = self._viber.parse_request(body)

        await self.handle_viber_request(viber_request)

        return Response(status_code=200)

    async def handle_viber_request(self, viber_request):
        handlers = {
            EventType.MESSAGE: self.handle_message,
            EventType.SUBSCRIBED: self.handle_subscribed,
            # EventType.FAILED: 3
        }

        handler = handlers.get(viber_request.event_type)

        if handler:
            return await handler(viber_request)

    async def handle_message(self, viber_request):
        if viber_request.message.tracking_data is None:
            return

        user = viber_request.sender

        dialog = await self.get_or_restore_dialog(user)

        if dialog:
            identifier = int(viber_request.message.tracking_data) + 1
            message = Message(identifier, viber_request.message.text)
            await dialog.handle_message(message)

    async def get_or_restore_dialog(self, user):
        if user.id in self.dialogs:
            return self.dialogs[user.id]

    async def handle_subscribed(self, viber_request):
        user = viber_request.user

        full_userdata = {
            "name": user.name,
            "avatar": user.avatar,
            "id": user.id,
            "country": user.country,
            "language": user.language,
            "api_version": user.api_version,
        }

        respondent = Respondent(
            id=user.id,
            messenger=self.type,
            username=user.name,
            extra_data=full_userdata,
        )

        dialog = await self.create_dialog(respondent)

        task = asyncio.ensure_future(self.quiz(dialog))
        self._tasks[user.id] = task

    async def send_message(self, user_id, message):
        if not isinstance(message, TextMessage):
            message = TextMessage(text=message)

        self._viber.send_messages(user_id, message)

        return message.tracking_data

    def set_webhook(self, url):
        events = self._viber.set_webhook(
            url, [EventType.MESSAGE, EventType.SUBSCRIBED, EventType.FAILED]
        )
        print(events)

    async def run_forever(self):
        await self._server.serve()

    async def stop(self):
        self._server.should_exit = True
