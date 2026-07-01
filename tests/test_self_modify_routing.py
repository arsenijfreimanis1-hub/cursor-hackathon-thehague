from jarvis.services import self_modify


def test_looks_like_self_modify_prefix():
    assert self_modify.looks_like_self_modify("improve yourself: add logging to planner")


def test_looks_like_self_modify_natural():
    assert self_modify.looks_like_self_modify("fix your code in the chat UI")


def test_extract_description():
    assert self_modify.extract_description("self-modify: add dark mode") == "add dark mode"


def test_looks_like_self_modify_open_ended():
    assert self_modify.looks_like_self_modify("improve yourself in any way you see fit")


def test_improve_run_minutes():
    assert self_modify.improve_run_minutes("improve-run: 45") == 45
    assert self_modify.improve_run_minutes("improve-run") == 30
