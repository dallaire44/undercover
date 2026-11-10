def get(client, path, **params):
    return client.get(path, params=params)


def test_contents_list_every_section(client):
    text = get(client, "/api/documents").text
    wording, manual = text.split("Claims manual (claims_manual):")
    assert wording.count("\n- ") == 12
    assert manual.count("\n- ") == 14
    assert "- 9. Repeat claims" in manual


def test_read_one_section(client):
    text = get(client, "/api/documents/claims_manual/sections/9").text
    assert text.startswith("Claims manual, 9. Repeat claims\n\n")
    assert "third claim within any 12 month period" in text
    assert "Meals without receipts" not in text
    assert "## " not in text


def test_read_unknown(client):
    path = "/api/documents/{}/sections/{}"
    assert get(client, path.format("claims_manual", "99")).status_code == 404
    assert get(client, path.format("evals", "1")).status_code == 404


def test_search_ranks_the_best_section_first(client):
    text = get(client, "/api/documents/search", query="wild animals").text
    assert text.splitlines()[0].startswith(
        "Claims manual, 7. Interpretation notes (claims_manual, 7): **Wild animals.**"
    )


def test_search_finds_meals_without_receipts(client):
    text = get(client, "/api/documents/search", query="meals receipts").text
    assert "Claims manual, 10. Meals without receipts" in text
    assert len(text.splitlines()) <= 5


def test_search_with_no_match(client):
    text = get(client, "/api/documents/search", query="zeppelin").text
    assert text == "No section matches 'zeppelin'."
