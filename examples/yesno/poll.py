from limpopo.question import Question


yesno_question = Question(
    topic="Choose yes or no!",
    choices={
        "yes": "Yes",
        "no": "No"
    }
)


def send_mail(question: str, answer: str):
    print(f"I'm sending mail with context: {question}: {answer}")


async def async_send_sms(question: str, answer: str):
    print(f"I'm sending sms with context: {question}: {answer}")


async def quiz(dialog):
    answer = await dialog.ask(yesno_question)

    if answer.text == yesno_question.choices["yes"]:
        await dialog.tell("Your choice is `Yes`")
        await dialog.call_once(send_mail, yesno_question.topic, answer.text)
    else:
        await dialog.tell("Your choice is `No`")
        await dialog.call_once(async_send_sms, yesno_question.topic, answer.text)
