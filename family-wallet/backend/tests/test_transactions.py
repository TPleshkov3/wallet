def setup_family(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")
    outsider_headers = auth_headers_factory("outsider@mail.ru", "abc123", "Outsider")

    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    client.post("/families/join", json={"code": family["invite_code"]}, headers=member_headers)
    return family, owner_headers, member_headers, outsider_headers


def test_add_income_success_201(client, auth_headers_factory):
    family, owner_headers, *_ = setup_family(client, auth_headers_factory)
    res = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "income",
            "amount": 100000,
            "category": "Зарплата",
            "description": "Аванс",
        },
        headers=owner_headers,
    )
    assert res.status_code == 201


def test_add_expense_success_201(client, auth_headers_factory):
    family, _, member_headers, _ = setup_family(client, auth_headers_factory)
    res = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "expense",
            "amount": 12000,
            "category": "Продукты",
            "description": "Пятерочка",
        },
        headers=member_headers,
    )
    assert res.status_code == 201


def test_add_transaction_to_foreign_family_forbidden(client, auth_headers_factory):
    family, _, _, outsider_headers = setup_family(client, auth_headers_factory)
    res = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "expense",
            "amount": 1,
            "category": "Другое",
        },
        headers=outsider_headers,
    )
    assert res.status_code == 403


def test_delete_own_transaction_success(client, auth_headers_factory):
    family, _, member_headers, _ = setup_family(client, auth_headers_factory)
    tx = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "expense",
            "amount": 12000,
            "category": "Продукты",
        },
        headers=member_headers,
    ).json()

    res = client.delete(f"/transactions/{tx['id']}?family_id={family['id']}", headers=member_headers)
    assert res.status_code == 200


def test_owner_can_delete_others_transaction(client, auth_headers_factory):
    family, owner_headers, member_headers, _ = setup_family(client, auth_headers_factory)
    tx = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "expense",
            "amount": 12000,
            "category": "Продукты",
        },
        headers=member_headers,
    ).json()

    res = client.delete(f"/transactions/{tx['id']}?family_id={family['id']}", headers=owner_headers)
    assert res.status_code == 200


def test_member_cannot_delete_others_transaction(client, auth_headers_factory):
    family, owner_headers, member_headers, _ = setup_family(client, auth_headers_factory)
    tx = client.post(
        "/transactions",
        json={
            "family_id": family["id"],
            "type": "income",
            "amount": 100000,
            "category": "Зарплата",
        },
        headers=owner_headers,
    ).json()

    res = client.delete(f"/transactions/{tx['id']}?family_id={family['id']}", headers=member_headers)
    assert res.status_code == 403
