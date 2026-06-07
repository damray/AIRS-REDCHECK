from sqlalchemy.orm import Session

from app.models import EvaluationError
from app.services.judge.schemas import EvaluationErrorCreate


class EvaluationErrorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, error: EvaluationErrorCreate) -> EvaluationError:
        evaluation_error = EvaluationError(
            dataset_id=error.dataset_id,
            stream_id=error.stream_id,
            attempt_id=error.attempt_id,
            portkey_gateway_profile_id=error.portkey_gateway_profile_id,
            error_code=error.error_code,
            message=error.message,
            raw_response=error.raw_response,
        )
        self.session.add(evaluation_error)
        self.session.commit()
        self.session.refresh(evaluation_error)
        return evaluation_error
