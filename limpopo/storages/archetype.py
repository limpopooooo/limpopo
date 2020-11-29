from abc import ABCMeta, abstractmethod


class ArchetypeStorage(metaclass=ABCMeta):
    @abstractmethod
    async def save_question_and_answer(self, dialog, question):
        pass

    @abstractmethod
    async def save_dialog(self, dialog):
        pass
