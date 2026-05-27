import json

def get_helper_message():
    return "helper"


def assert_validation_error(
    status: int,
    status_expected: int,
    detail: dict | None = None,
    *,
    type_prefix: str | list[str] | None = None,
    loc_contains: str | None = None,
    ctx_contains: dict | list[dict] | None = None,
    body_length: int | None = None,
    body_item: dict | None = None,
    uuid: str | None = None,
    uuid_expected: str | None = None,
    caption: str | dict | None = None,
    caption_item: str | None = None,
    caption_expected: str | None = None,
    msg_substring: str | None = None,
) -> None:
    assert status == status_expected

    prefixes = [type_prefix] if isinstance(type_prefix, str) else type_prefix
    if prefixes is not None:
        assert any(
            detail["type"].startswith(prefix)
            for prefix in prefixes
        )

    if loc_contains is not None:
        if isinstance(loc_contains, str):
            loc_string = json.dumps(detail["loc"], separators=(",", ":"))
            assert loc_contains in loc_string
        else:
            assert loc_contains in detail["loc"]

    ctx_list = [ctx_contains] if isinstance(ctx_contains, dict) else ctx_contains
    if ctx_list is not None:
        # требуем, чтобы хотя бы один ожидаемый набор ключей/значений совпал
        assert any(
            all(key in detail["ctx"] and detail["ctx"][key] == value
                for key, value in expected.items())
            for expected in ctx_list
        )

    if body_length is not None:
        assert len(detail) == body_length

    if body_item is not None:
        assert all(
            all(key in item and isinstance(item[key], value)
                for key, value in body_item.items())
            for item in detail
        )

    if uuid is not None and uuid_expected is not None:
        assert detail["uuid"] == uuid_expected

    if caption is not None and caption_expected is not None:
        assert caption_expected in caption

    """
    if caption_expected is not None:
        assert detail["caption"] == caption_expected
    elif (caption is not None and isinstance(caption, dict)
          and caption_item is not None):
        assert all(
            key in detail["caption"] and detail["caption"][key] == value
            for key, value in caption.items()
        )
    """

    if msg_substring is not None:
        assert msg_substring in detail["msg"].lower()