from app.container import container


def test_create_returns_a_new_user_id_that_exists():
    user_id = container.users.create()

    assert user_id
    assert container.users.exists(user_id)


def test_exists_is_false_for_unknown_user():
    assert container.users.exists("does-not-exist") is False
