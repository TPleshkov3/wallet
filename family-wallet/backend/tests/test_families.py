def test_create_family_returns_invite_code(client, auth_headers_factory):
    headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    res = client.post("/families", json={"name": "Ивановы"}, headers=headers)
    body = res.json()

    assert res.status_code == 201
    assert len(body["invite_code"]) == 6


def test_join_family_by_code_success(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")

    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    res = client.post(
        "/families/join",
        json={"code": family["invite_code"]},
        headers=member_headers,
    )

    assert res.status_code == 200
    assert res.json()["family_id"] == family["id"]


def test_join_family_wrong_code(client, auth_headers_factory):
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")
    res = client.post("/families/join", json={"code": "ZZZZZZ"}, headers=member_headers)
    assert res.status_code == 404


def test_owner_can_get_invite_code(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    res = client.get(f"/families/{family['id']}/invite", headers=owner_headers)

    assert res.status_code == 200
    assert res.json()["invite_code"] == family["invite_code"]


def test_member_cannot_get_invite_code(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")
    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    client.post("/families/join", json={"code": family["invite_code"]}, headers=member_headers)

    res = client.get(f"/families/{family['id']}/invite", headers=member_headers)
    assert res.status_code == 403


def test_member_can_get_family_members_list(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")
    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    client.post("/families/join", json={"code": family["invite_code"]}, headers=member_headers)

    res = client.get(f"/families/{family['id']}/members", headers=member_headers)
    names = {item["user_name"] for item in res.json()}

    assert res.status_code == 200
    assert names == {"Owner", "Member"}
