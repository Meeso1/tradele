from app.container import container


def test_has_completed_tutorial_defaults_to_false():
    user_id = container.users.create()

    assert container.tutorial_repository.has_completed_tutorial(user_id) is False


def test_has_completed_tutorial_returns_false_for_unknown_user():
    assert container.tutorial_repository.has_completed_tutorial("no-such-user") is False


def test_mark_tutorial_completed_persists():
    user_id = container.users.create()

    container.tutorial_repository.mark_tutorial_completed(user_id)

    assert container.tutorial_repository.has_completed_tutorial(user_id) is True


def test_mark_tutorial_completed_is_idempotent():
    user_id = container.users.create()

    container.tutorial_repository.mark_tutorial_completed(user_id)
    container.tutorial_repository.mark_tutorial_completed(user_id)

    assert container.tutorial_repository.has_completed_tutorial(user_id) is True


def test_tutorial_state_is_tracked_per_user():
    first = container.users.create()
    second = container.users.create()

    container.tutorial_repository.mark_tutorial_completed(first)

    assert container.tutorial_repository.has_completed_tutorial(first) is True
    assert container.tutorial_repository.has_completed_tutorial(second) is False
