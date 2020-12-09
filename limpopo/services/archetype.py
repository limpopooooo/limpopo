import logging

from abc import ABCMeta, abstractmethod
from asyncio import wait_for, Queue, TimeoutError
from copy import copy
import typing

from .. import const
from ..dto import Answer, Message, Respondent
from ..exceptions import QuestionWrongAnswer
from ..question import Question


class ArchetypeService(metaclass=ABCMeta):
    def __init__(self, quiz, storage, settings, cls_dialog, *args, **kwargs):
        self.dialogs = {}
        self.quiz = quiz
        self.storage = storage
        self.settings = settings
        self.cls_dialog = cls_dialog

    async def run_quiz(self, dialog):
        try:
            await self.quiz(dialog)
            await self.close_dialog(dialog.respondent.id, is_complete=True)
        except TimeoutError:
            logging.info("Dialog #{} removed due to timeout")
            await self.close_dialog(dialog.respondent.id, is_complete=None)

    async def close_dialog(
        self, respondent_id: str, is_complete: typing.Optional[bool]
    ):
        dialog = self.dialogs.pop(respondent_id, None)
        if dialog:
            if is_complete is not None:
                await dialog.on_close(is_complete)
            logging.info("Dialog {} was closed".format(dialog.id))
        else:
            logging.info(
                "Dialog with respondent: {} doesn't found".format(respondent_id)
            )

    async def create_dialog(
        self, respondent: Respondent, identifier=None, prepared_questions=None
    ):
        dialog = self.cls_dialog(
            self,
            respondent,
            prepared_questions=prepared_questions,
            **self.settings.get("dialog", {}),
        )

        if identifier:
            dialog.set_restore_mode()
        else:
            identifier = await dialog.on_start()

        dialog.set_identifier(identifier)

        self.dialogs[respondent.id] = dialog

        logging.info(
            "New dialog #{} was created for respondent: {}".format(
                identifier, respondent.id
            )
        )

        return dialog

    @property
    @abstractmethod
    def type(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def run_forever(self):
        pass

    @abstractmethod
    async def send_message(self, user_id, *args, **kwargs):
        pass


class ArchetypeDialog(metaclass=ABCMeta):
    def __init__(
        self,
        service: ArchetypeService,
        respondent: Respondent,
        answer_timeout: int = const.ANSWER_TIMEOUT,
        prepared_questions=None,
        *args,
        **kwargs,
    ):
        self.id = None

        self.service = service
        self.respondent = respondent

        self.last_question_id = 0
        self.answer = Answer()
        self.prepared_questions = prepared_questions or {}
        self.answer_timeout = answer_timeout

        self._queue_answers = Queue(10)
        self._restore_mode = False

    def set_restore_mode(self):
        self._restore_mode = True

    def set_identifier(self, identifier: str):
        self.id = identifier

    @abstractmethod
    def prepare_question(self, question: Question) -> dict:
        pass

    @abstractmethod
    def prepare_answer(self, question: Question, answer: Answer) -> Answer:
        pass

    async def ask(self, question: Question) -> Answer:
        self.answer.clear()

        if question.topic in self.prepared_questions:
            answer_text = self.prepared_questions[question.topic]
            self.answer.set(answer_text)
            return copy(self.answer)

        if not self._restore_mode:
            message_data = self.prepare_question(question)
            self.last_question_id = await self.tell(message_data)

        self._restore_mode = False

        while 1:
            try:
                message = await wait_for(self._queue_answers.get(), self.answer_timeout)

                if message.id < self.last_question_id:
                    continue

                self.answer.set(message.text)
                self.answer = self.prepare_answer(question, self.answer)

                question.validate_answer(self.answer)

                await self.service.storage.save_question_and_answer(self, question)

                return copy(self.answer)
            except QuestionWrongAnswer:
                await self.tell(const.WRONG_ANSWER_FORMAT)
                self.answer.clear()

    async def tell(self, *args, **kwargs) -> int:
        return await self.service.send_message(self.respondent.id, *args, **kwargs)

    async def handle_message(self, message: Message):
        await self._queue_answers.put(message)

    async def on_start(self):
        return await self.service.storage.create_dialog(self)

    async def on_close(self, is_complete):
        await self.service.storage.close_dialog(self, is_complete)
