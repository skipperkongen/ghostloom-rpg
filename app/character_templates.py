"""Fixed character creation questionnaire templates."""

from app.schemas.games import CharacterQuestionnaire, Question, QuestionChoice


UNIVERSAL_QUESTIONNAIRE = CharacterQuestionnaire(
    questions=[
        Question(
            id="q1",
            text="What is your character's primary strength?",
            choices=[
                QuestionChoice(id="c1", label="Physical prowess"),
                QuestionChoice(id="c2", label="Sharp intellect"),
                QuestionChoice(id="c3", label="Charisma and leadership"),
            ],
        ),
        Question(
            id="q2",
            text="How does your character approach challenges?",
            choices=[
                QuestionChoice(id="c1", label="Head-on and direct"),
                QuestionChoice(id="c2", label="Careful planning and strategy"),
                QuestionChoice(id="c3", label="Diplomacy and negotiation"),
            ],
        ),
        Question(
            id="q3",
            text="What role do you naturally take in a group?",
            choices=[
                QuestionChoice(id="c1", label="Front-line protector"),
                QuestionChoice(id="c2", label="Knowledge seeker and analyst"),
                QuestionChoice(id="c3", label="Social connector and motivator"),
            ],
        ),
        Question(
            id="q4",
            text="What best describes your character's temperament?",
            choices=[
                QuestionChoice(id="c1", label="Bold and impulsive"),
                QuestionChoice(id="c2", label="Cautious and observant"),
                QuestionChoice(id="c3", label="Adaptable and witty"),
            ],
        ),
    ]
)

QUESTION_LABELS = {q.id: q.text for q in UNIVERSAL_QUESTIONNAIRE.questions}
CHOICE_LABELS = {
    q.id: {c.id: c.label for c in q.choices}
    for q in UNIVERSAL_QUESTIONNAIRE.questions
}


def get_questionnaire_for_seed(seed: str) -> CharacterQuestionnaire:
    """Return questionnaire template for a game seed (v1: universal template)."""
    _ = seed
    return UNIVERSAL_QUESTIONNAIRE


def build_character_profile(answers: list[dict]) -> dict:
    """Derive a character profile from questionnaire answers."""
    traits: list[str] = []
    for answer in answers:
        question_id = answer.get("question_id", "")
        choice_id = answer.get("choice_id", "")
        choice_label = CHOICE_LABELS.get(question_id, {}).get(choice_id)
        if choice_label:
            traits.append(choice_label)
    return {
        "traits": traits,
        "summary": ", ".join(traits) if traits else "An adaptable adventurer",
    }


def validate_answers(answers: list[dict]) -> list[str]:
    """Return list of validation errors for answers."""
    errors: list[str] = []
    required_ids = {q.id for q in UNIVERSAL_QUESTIONNAIRE.questions}
    provided_ids = {a.get("question_id") for a in answers}
    for question_id in required_ids - provided_ids:
        errors.append(f"Missing answer for question {question_id}")
    for answer in answers:
        question_id = answer.get("question_id", "")
        choice_id = answer.get("choice_id", "")
        if question_id not in CHOICE_LABELS:
            errors.append(f"Unknown question_id: {question_id}")
            continue
        if choice_id not in CHOICE_LABELS[question_id]:
            errors.append(f"Unknown choice_id {choice_id} for question {question_id}")
    return errors
