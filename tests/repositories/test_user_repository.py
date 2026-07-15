from app.container import container


def test_insert_then_exists_returns_true():
    container.user_repository.insert("u1", "now")

    assert container.user_repository.exists("u1") is True


def test_exists_is_false_for_unknown_user():
    assert container.user_repository.exists("does-not-exist") is False
