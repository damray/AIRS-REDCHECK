from app.parsers.agent_json import AgentJsonParser
from app.parsers.base import SourceParser
from app.parsers.static_json import StaticJsonParser

PARSERS: tuple[SourceParser, ...] = (AgentJsonParser(), StaticJsonParser())


def detect_parser(payload: object) -> SourceParser | None:
    for parser in PARSERS:
        if parser.can_parse(payload):
            return parser
    return None
