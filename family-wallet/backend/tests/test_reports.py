def setup_family_with_data(client, auth_headers_factory):
    owner_headers = auth_headers_factory("owner@mail.ru", "abc123", "Owner")
    member_headers = auth_headers_factory("member@mail.ru", "abc123", "Member")

    family = client.post("/families", json={"name": "Ивановы"}, headers=owner_headers).json()
    client.post("/families/join", json={"code": family["invite_code"]}, headers=member_headers)
    return family, owner_headers, member_headers


def test_empty_report_all_zeros(client, auth_headers_factory):
    family, owner_headers, _ = setup_family_with_data(client, auth_headers_factory)
    res = client.get(f"/report?family_id={family['id']}&year=2026&month=4", headers=owner_headers)

    assert res.status_code == 200
    assert res.json()["total_income"] == 0
    assert res.json()["total_expense"] == 0
    assert res.json()["balance"] == 0
    assert res.json()["by_category"] == {}


def test_report_totals_calculated_correctly(client, auth_headers_factory):
    family, owner_headers, member_headers = setup_family_with_data(client, auth_headers_factory)

    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "income", "amount": 100000, "category": "Зарплата"},
        headers=owner_headers,
    )
    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "expense", "amount": 25000, "category": "Продукты"},
        headers=member_headers,
    )
    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "expense", "amount": 6000, "category": "Транспорт"},
        headers=member_headers,
    )

    res = client.get(f"/report?family_id={family['id']}&year=2026&month=4", headers=owner_headers)
    body = res.json()

    assert res.status_code == 200
    assert body["total_income"] == 100000
    assert body["total_expense"] == 31000
    assert body["balance"] == 69000


def test_report_expenses_grouped_by_category(client, auth_headers_factory):
    family, owner_headers, member_headers = setup_family_with_data(client, auth_headers_factory)

    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "expense", "amount": 2000, "category": "Продукты"},
        headers=member_headers,
    )
    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "expense", "amount": 3000, "category": "Продукты"},
        headers=member_headers,
    )
    client.post(
        "/transactions",
        json={"family_id": family["id"], "type": "expense", "amount": 1000, "category": "Транспорт"},
        headers=owner_headers,
    )

    res = client.get(f"/report?family_id={family['id']}&year=2026&month=4", headers=owner_headers)
    by_category = res.json()["by_category"]

    assert by_category["Продукты"] == 5000
    assert by_category["Транспорт"] == 1000
