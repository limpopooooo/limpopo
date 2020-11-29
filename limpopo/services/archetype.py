from abc import ABCMeta, abstractmethod

from asyncio import Event, wait_for
from copy import copy

from .. import const
from ..dto import Answer, Message
from ..exceptions import QuestionWrongAnswer
from ..question import Question


class ArchetypeService(metaclass=ABCMeta):
    def __init__(self, quiz, storage, settings, *args, **kwargs):
        self.stop_event = Event()
        self.dialogs = {}
        self.quiz = quiz
        self.storage = storage
        self.settings = settings

    @property
    @abstractmethod
    def type(self):
        pass

    def stop(self):
        self.stop_event.set()

    @abstractmethod
    def run_forever(self):
        pass

    @abstractmethod
    async def send_message(self, user_id, *args, **kwargs):
        pass


class ArchetypeDialog(metaclass=ABCMeta):
    def __init__(
        self,
        service: ArchetypeService,
        identifier: int,
        username: str,
        answer_timeout: int = const.ANSWER_TIMEOUT
    ):
        self.service = service
        self.identifier = identifier
        self.username = username
        self.last_question_id = 0
        self.answer = Answer()
        self.answer_timeout = answer_timeout

    @abstractmethod
    def prepare_question(self, question: Question) -> dict:
        pass

    @abstractmethod
    def prepare_answer(self, question: Question, answer: Answer) -> Answer:
        pass

    async def ask(self, question: Question) -> Answer:
        self.answer.clear()

        message_data = self.prepare_question(question)

        self.last_question_id = await self.tell(**message_data)

        while 1:
            try:
                await wait_for(self.answer.wait(), self.answer_timeout)

                self.answer = self.prepare_answer(question, self.answer)

                question.validate_answer(self.answer)

                await self.service.storage.save_question_and_answer(self, question)

                return copy(self.answer)
            except QuestionWrongAnswer:
                await self.tell(const.WRONG_ANSWER_FORMAT)
                self.answer.clear()

    async def tell(self, *args, **kwargs) -> int:
        return await self.service.send_message(self.identifier, *args, **kwargs)

    async def handle_message(self, message: Message):
        if message.id < self.last_question_id:
            return

        self.answer.set(message.text)

    async def start(self):
        await self.service.storage.save_dialog(self)

    async def close(self):
        pass
