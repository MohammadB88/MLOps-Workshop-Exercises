import io
import json
import logging

from rivercast.log import configure_logging, get_logger


def _capture_one_line(emit) -> dict:
    stream = io.StringIO()
    configure_logging(level=logging.DEBUG, stream=stream)
    emit()
    lines = [line for line in stream.getvalue().splitlines() if line]
    assert len(lines) == 1
    return json.loads(lines[0])


def test_log_lines_are_json_with_required_fields() -> None:
    entry = _capture_one_line(lambda: get_logger("test").info("hello"))
    assert entry["level"] == "INFO"
    assert entry["logger"] == "rivercast.test"
    assert entry["message"] == "hello"
    # UTC ISO-8601 with offset.
    assert entry["timestamp"].endswith("+00:00")


def test_extra_context_is_merged_into_json() -> None:
    entry = _capture_one_line(
        lambda: get_logger("test").info("fetched", extra={"station_uuid": "abc", "rows": 42})
    )
    assert entry["station_uuid"] == "abc"
    assert entry["rows"] == 42


def test_exceptions_are_serialized() -> None:
    def emit() -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            get_logger("test").exception("failed")

    entry = _capture_one_line(emit)
    assert entry["level"] == "ERROR"
    assert "ValueError: boom" in entry["exception"]


def test_configure_is_idempotent_no_duplicate_lines() -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)
    configure_logging(stream=stream)
    get_logger("test").info("once")
    lines = [line for line in stream.getvalue().splitlines() if line]
    assert len(lines) == 1
