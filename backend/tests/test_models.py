from sqlalchemy.orm import Session

from app.models import Attempt, Dataset, Stream


def test_static_record_can_be_represented_as_one_stream_one_attempt(
    db_session: Session,
) -> None:
    dataset = Dataset(
        source_content_type="application/json",
        detected_format="static_json",
        parser_version="static-json-v1",
        raw_payload=[{"prompt": "p", "output": "o", "threat": True}],
        import_status="imported",
        stream_count=1,
        attempt_count=1,
        error_count=0,
    )
    stream = Stream(
        dataset=dataset,
        input_type="static",
        raw_payload={"prompt": "p", "output": "o", "threat": True},
        stream_metadata={},
    )
    attempt = Attempt(
        dataset=dataset,
        stream=stream,
        attempt_index=0,
        source_prompt="p",
        source_output="o",
        source_threat_raw="True",
        source_threat_normalized="THREAT",
        raw_payload={"prompt": "p", "output": "o", "threat": True},
        attempt_metadata={},
    )

    db_session.add(dataset)
    db_session.add(stream)
    db_session.add(attempt)
    db_session.commit()

    persisted = db_session.query(Dataset).one()
    assert persisted.raw_payload == [{"prompt": "p", "output": "o", "threat": True}]
    assert len(persisted.streams) == 1
    assert len(persisted.attempts) == 1


def test_agent_record_can_be_represented_as_one_stream_many_attempts(
    db_session: Session,
) -> None:
    dataset = Dataset(
        source_content_type="application/json",
        detected_format="agent_json",
        parser_version="agent-json-v1",
        raw_payload=[{"stream_id": "s1"}],
        import_status="imported",
        stream_count=1,
        attempt_count=2,
        error_count=0,
    )
    stream = Stream(
        dataset=dataset,
        external_stream_id="s1",
        input_type="agent",
        goal="goal",
        stream_threat_raw="False",
        raw_payload={"stream_id": "s1"},
        stream_metadata={},
    )
    for index in range(2):
        db_session.add(
            Attempt(
                dataset=dataset,
                stream=stream,
                attempt_index=index,
                source_prompt=f"p{index}",
                source_output=f"o{index}",
                source_threat_raw="False",
                source_threat_normalized="SAFE",
                raw_payload={"iteration": index},
                attempt_metadata={},
            )
        )

    db_session.add(dataset)
    db_session.add(stream)
    db_session.commit()

    persisted = db_session.query(Stream).one()
    assert persisted.raw_payload == {"stream_id": "s1"}
    assert [attempt.attempt_index for attempt in persisted.attempts] == [0, 1]
