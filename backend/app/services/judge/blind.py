from app.models import Attempt
from app.services.judge.rubric import DEFAULT_RESPONSE_RUBRIC, DEFAULT_SYSTEM_PROMPT
from app.services.judge.schemas import JudgeRequest


def build_blind_judge_request(
    attempt: Attempt,
    goal: str | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    rubric: str = DEFAULT_RESPONSE_RUBRIC,
) -> JudgeRequest:
    return JudgeRequest(
        system_prompt=system_prompt,
        prompt=attempt.source_prompt,
        output=attempt.source_output,
        goal=goal,
        rubric=rubric,
    )
