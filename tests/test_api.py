def test_health_reports_the_loaded_database(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["sets"] == 2
    assert body["cards"] == 3


def test_lookup_accepts_a_set_code_and_a_bare_number(client):
    body = client.get("/v1/lookup", params={"set": "SVI", "number": "4"}).json()
    assert body["matches"] == 1
    assert body["items"][0]["card_name"] == "Sprigatito"


def test_lookup_accepts_the_number_as_printed_with_the_set_size(client):
    body = client.get("/v1/lookup", params={"set": "SVI", "number": "004/198"}).json()
    assert body["matches"] == 1


def test_lookup_accepts_a_set_name_as_well_as_a_code(client):
    body = client.get("/v1/lookup", params={"set": "Scarlet & Violet", "number": "004"}).json()
    assert body["matches"] == 1


def test_lookup_keeps_the_alphabetic_prefix_of_a_number(client):
    assert client.get("/v1/lookup", params={"set": "SVI", "number": "TG12"}).json()["matches"] == 1
    # 12 without the prefix is a different card, and is not in this set.
    assert client.get("/v1/lookup", params={"set": "SVI", "number": "12"}).json()["matches"] == 0


def test_lookup_finds_a_japanese_card_by_its_english_set_name(client):
    body = client.get("/v1/lookup", params={"set": "Scarlet ex", "number": "1"}).json()
    assert body["matches"] == 1
    assert body["items"][0]["card_name"] == "リザードン"
    assert body["items"][0]["card_name_en"] == "Charizard"


def test_cards_can_be_searched_in_english_across_languages(client):
    body = client.get("/v1/cards", params={"q": "Charizard"}).json()
    assert body["total"] == 1
    assert body["items"][0]["language"] == "ja"


def test_cards_can_be_filtered_by_language_and_set_code(client):
    body = client.get("/v1/cards", params={"language": "en", "set_code": "SVI"}).json()
    assert body["total"] == 2


def test_set_cards_are_returned_in_printed_order(client):
    body = client.get("/v1/sets/pokemon:en:svi/cards").json()
    assert [item["card_number"] for item in body["items"]] == ["004", "TG12"]


def test_unknown_set_returns_404(client):
    assert client.get("/v1/sets/pokemon:en:nope").status_code == 404


def test_languages_lists_coverage(client):
    body = client.get("/v1/languages").json()
    assert {row["code"] for row in body} == {"en", "ja"}


def test_games_lists_coverage(client):
    body = client.get("/v1/games").json()
    assert body[0]["game"] == "pokemon"
    assert body[0]["kind"] == "tcg"
    assert body[0]["sets"] == 2


def test_sets_and_cards_accept_a_game_filter(client):
    sets = client.get("/v1/sets", params={"game": "pokemon"}).json()
    assert sets["total"] == 2
    empty = client.get("/v1/sets", params={"game": "mtg"}).json()
    assert empty["total"] == 0

    cards = client.get("/v1/cards", params={"game": "pokemon", "language": "en"}).json()
    assert cards["total"] == 2
    lookup = client.get(
        "/v1/lookup", params={"set": "SVI", "number": "4", "game": "pokemon"}
    ).json()
    assert lookup["matches"] == 1


def test_refresh_requires_a_configured_token(client):
    assert client.post("/v1/admin/refresh").status_code == 503


def test_refresh_rejects_a_wrong_token(client, monkeypatch):
    monkeypatch.setenv("POKEDB_ADMIN_TOKEN", "secret")
    response = client.post("/v1/admin/refresh", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
