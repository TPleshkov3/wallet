def test_register_success(client):
    res = client.post(
        "/auth/register",
        json={"email": "m@mail.ru", "password": "abc123", "name": "Маша"},
    )
    assert res.status_code == 201


def test_register_duplicate_email(client):
    payload = {"email": "m@mail.ru", "password": "abc123", "name": "Маша"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 400


def test_login_success_returns_token(client):
    client.post(
        "/auth/register",
        json={"email": "m@mail.ru", "password": "abc123", "name": "Маша"},
    )
    res = client.post("/auth/login", json={"email": "m@mail.ru", "password": "abc123"})
    assert res.status_code == 200
    assert "token" in res.json()


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "m@mail.ru", "password": "abc123", "name": "Маша"},
    )
    res = client.post("/auth/login", json={"email": "m@mail.ru", "password": "wrong"})
    assert res.status_code == 401
