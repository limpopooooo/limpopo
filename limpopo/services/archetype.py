import asyncio
import logging
import typing
from abc import ABCMeta, abstractmethod
from asyncio import CancelledError, Queue, TimeoutError, create_task, wait_for
from copy import copy
from dataclasses import dataclass

from tenacity import RetryError

from .. import const
from ..dto import Answer, Message, Respondent
from ..exceptions import DialogStopped, QuestionWrongAnswer, SettingsError
from ..helpers import calculate_functions_hash, with_retry
from ..question import Question


class EmptySettings:
    def __post_init__(self):
        pass


@dataclass
class DefaultSettings(EmptySettings):
    answer_timeout: int = const.ANSWER_TIMEOUT
    reply_without_dialogue: bool = True
    start_command: str = "/start"
    cancel_command: str = "/cancel"
    pause_command: str = "/pause"

    def __post_init__(self):
        super().__post_init__()

        if not isinstance(self.answer_timeout, int):
            raise SettingsError(
                "Settings field `answer_timeout` must be of the int type"
            )

        if not isinstance(self.reply_without_dialogue, bool):
            raise SettingsError(
                "Settings field `reply_without_dialogue` must be of the bool type"
            )

        if not isinstance(self.start_command, str):
            raise SettingsError(
                "Settings field `start_command` must be of the str type"
            )

        if not isinstance(self.cancel_command, str):
            raise SettingsError(
                "Settings field `cancel_command` must be of the str type"
            )

        if not isinstance(self.pause_command, str):
            raise SettingsError(
                "Settings field `pause_command` must be of the str type"
            )


class ArchetypeService(metaclass=ABCMeta):
    def __init__(self, quiz, storage, settings, cls_dialog, *args, **kwargs):
        if not isinstance(settings, DefaultSettings):
            raise SettingsError(
                "Passed wrong params `settings`, must be DefaultSettings instance"
            )

        self.dialogs = {}
        self.quiz = quiz
        self.storage = storage
        self.settings = settings
        self.cls_dialog = cls_dialog

    async def run_quiz(self, dialog):
        logging.info("Task for dialog #{} started".format(dialog.id))

        try:
            dialog.run_task(self.quiz)
            await dialog.task
            await self.close_dialog(dialog.respondent.id, is_complete=True)
        except TimeoutError:
            logging.info("Dialog #{} removed due to timeout".format(dialog.id))
            await self.close_dialog(dialog.respondent.id, is_complete=None)
        except (CancelledError, DialogStopped):
            pass
        except Exception:
            logging.exception("Catch exception in run_quiz:")
        finally:
            logging.info("Task for dialog #{} stopped".format(dialog.id))

    async def close_dialog(
        self, respondent_id: str, is_complete: typing.Optional[bool]
    ):
        dialog = self.dialogs.pop(respondent_id, None)
        if dialog:
            if dialog.task:
                logging.info("Dialog #{} task cancelling".format(dialog.id))
                dialog.task.cancel()

            if is_complete is not None:
                await dialog.on_close(is_complete)
                logging.info("Dialog #{} was closed".format(dialog.id))
        else:
            logging.info(
                "Dialog with respondent #{} doesn't found".format(respondent_id)
            )

    async def create_dialog(
        self,
        respondent: Respondent,
        identifier=None,
        prepared_questions=None,
        called_functions=None,
        repeat_last_question=False,
    ):
        dialog = self.cls_dialog(
            self,
            respondent,
            prepared_questions=prepared_questions,
            called_functions=called_functions,
            answer_timeout=self.settings.answer_timeout,
        )

        if identifier:
            dialog.set_restore_mode()
            dialog.set_repeat_last_question(repeat_last_question)
        elif identifier is None:
            identifier = await dialog.on_start()

        dialog.set_identifier(identifier)

        self.dialogs[respondent.id] = dialog

        logging.info(
            "New dialog #{} was created for respondent #{}".format(
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
    async def run_forever(self, *args, **kwargs):
        pass

    @abstractmethod
    async def send_message(self, user_id, *args, **kwargs) -> int:
        return 1


class ArchetypeDialog(metaclass=ABCMeta):
    def __init__(
        self,
        service: ArchetypeService,
        respondent: Respondent,
        answer_timeout: int = const.ANSWER_TIMEOUT,
        prepared_questions=None,
        called_functions=None,
        *args,
        **kwargs,
    ):
        self.id = None

        self.service = service
        self.respondent = respondent

        self.task = None
        self.last_question_id = 0
        self.answer = Answer()
        self.prepared_questions = prepared_questions or {}
        self.called_functions = called_functions or set()
        self.answer_timeout = answer_timeout

        self._queue_answers = Queue(10)
        self._restore_mode = False
        self._repeat_last_question = False

    def set_restore_mode(self):
        self._restore_mode = True

    def set_repeat_last_question(self, value):
        self._repeat_last_question = value

    def set_identifier(self, identifier: str):
        self.id = identifier

    @abstractmethod
    def prepare_question(self, question: Question) -> dict:
        pass

    @abstractmethod
    def prepare_answer(self, question: Question, answer: Answer) -> Answer:
        pass

    def run_task(self, func):
        self.task = create_task(func(self))

    async def ask(self, question: Question) -> Answer:
        self.answer.clear()

        if question.plain_text in self.prepared_questions:
            answer_text = self.prepared_questions[question.plain_text]
            self.answer.set(answer_text)
            return copy(self.answer)

        if not self._restore_mode or self._repeat_last_question:
            message_data = self.prepare_question(question)
            self.last_question_id = await self.tell(
                message_data, force=self._repeat_last_question
            )

        self._restore_mode = False

        while 1:
            try:
                message = await wait_for(self._queue_answers.get(), self.answer_timeout)

                if message.id < self.last_question_id:
                    continue

                self.answer.set(message.text)
                self.answer = self.prepare_answer(question, self.answer)

                question.validate_answer(self.answer)

                try:
                    await with_retry(
                        lambda: self.service.storage.save_question_and_answer(
                            self, question
                        ),
                        exceptions=self.service.storage.io_exceptions,
                        stop_callback_coro=self.service.stop,
                    )
                except RetryError:
                    logging.error(
                        "Dialog #{} stopped due to Storage IO error".format(self.id)
                    )
                    raise DialogStopped(self.id)

                return copy(self.answer)
            except QuestionWrongAnswer:
                await self.tell(const.WRONG_ANSWER_FORMAT, keep_keyboard=True)
                self.answer.clear()

    async def tell(self, *args, force=False, **kwargs) -> int:
        if self._restore_mode and not force:
            return 0
        return await self.service.send_message(self.respondent.id, *args, **kwargs)

    async def call_once(self, func: typing.Callable, *args, **kwargs) -> typing.Any:
        funcs_hash = calculate_functions_hash(func)

        if funcs_hash not in self.called_functions:
            try:
                await with_retry(
                    lambda: self.service.storage.save_function_call(self, funcs_hash),
                    exceptions=self.service.storage.io_exceptions,
                    stop_callback_coro=self.service.stop,
                )
            except RetryError:
                logging.error(
                    "Dialog #{} stopped due to Storage IO error".format(self.id)
                )
                raise DialogStopped(self.id)

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

    async def handle_message(self, message: Message):
        await self._queue_answers.put(message)

    async def pause(self):
        done = await self.service.storage.pause(self)

        if done:
            logging.info("Dialog #{} on pause".format(self.id))
        else:
            logging.warning("Dialog #{} already on pause".format(self.id))

    async def on_start(self):
        return await with_retry(
            lambda: self.service.storage.create_dialog(self),
            exceptions=self.service.storage.io_exceptions,
            stop_callback_coro=self.service.stop,
        )

    async def on_close(self, is_complete):
        await with_retry(
            lambda: self.service.storage.close_dialog(self, is_complete),
            exceptions=self.service.storage.io_exceptions,
            stop_callback_coro=self.service.stop,
        )
