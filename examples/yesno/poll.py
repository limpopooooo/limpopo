from limpopo.question import Question


yesno_question = Question(
    topic="Choose yes or no!",
    choices={
        "yes": "Yes",
        "no": "No"
    }
)


async def quiz(dialog):
    answer = await dialog.ask(yesno_question)

    if answer.text == yesno_question.choices["yes"]:
        await dialog.tell("Your choice is `Yes`")
    else:
        await dialog.tell("Your choice is `No`")
