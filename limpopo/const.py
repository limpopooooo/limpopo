ANSWER_TIMEOUT = 300  # 300 sec. timeout to answer in dialog

FOREWORD = "Для прохождения опроста, пожалуйста напишите {start_command}"

CANCEL = "Опрос отменён! Если Вы передумаете в будущем, то начните опрос заново, используя команду {start_command}"

WRONG_ANSWER_FORMAT = "Некорректный формат ответа!"

SESSION_DOESNT_EXIST = "У вас в данный момент нет ни одного активного диалога."

DIALOG_ON_PAUSE = "Опрос поставлен на паузу"
PAUSE_CANCELLED = "Диалог снят с паузы"

LIMPOPO_AVATAR = "https://www.svgrepo.com/show/165367/ghost.svg"


VIBER_INTO_MESSAGE = {
    "text": (
        "Здравствуйте!\n"
        "Для прохождения опроса "
        "нажмите кнопку \"Начать\" или зайдите в профиль бота и разрешите ему передавать Вам сообщения"
        ),
    "keyboard": {
        "Type": "keyboard",
        "Buttons": [{
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "ActionType": "reply",
            "ActionBody": "/start",
            "ReplyType": "message",
            "Text": "НАЧАТЬ",
        }],
    }
}
