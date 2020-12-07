import asyncio

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration

from .archetype import ArchetypeDialog, ArchetypeService
from ..const import LIMPOPO_AVATAR
from ..dto import Message, Messengers, Respondent


class ViberDialog(ArchetypeDialog):
    def prepare_message(self, question):
        message = question.topic

        buttons = []
        if question.options:
            for option in question.options:
                buttons.append(option)

        return {"message": message, "buttons": buttons}


class HTTPServer:
    def __init__(self, queue):
        self.queue = queue


class ViberService(ArchetypeService):
    type = Messengers.viber

    def __init__(
        self, quiz, storage, settings, cls_dialog=ViberDialog, *args, **kwargs
    ):
        super().__init__(quiz, storage, settings, cls_dialog=cls_dialog)

        self.viber = Api(
            BotConfiguration(
                name=settings["viber_name"],
                avatar=settings.get("viber_avatar", LIMPOPO_AVATAR),
                auth_token=settings.get("viber_bot_token"),
            )
        )

        self.app = Starlette(
            routes=[Route("/", endpoint=self.handle_http_request, methods=["POST", "GET"])]
        )

    async def handle_http_request(self, request):
        body = await request.body()
        signature = request.headers.get("X-Viber-Content-Signature")

        if not self.viber.verify_signature(body, signature):
            return Response(status_code=403)

        viber_request = self.viber.parse_request(body)

        await self.handle_viber_request(viber_request)

        return Response(status_code=200)

    async def handle_viber_request(self, viber_request):
        pass

    def run_forever(self):
        pass

    async def send_message(self, user_id, *args, **kwargs):
        pass
