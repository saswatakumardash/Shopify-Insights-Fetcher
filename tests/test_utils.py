from app.utils import normalize_url, find_emails, find_phones


def test_normalize_url():
    assert normalize_url("example.com").startswith("https://example.com")
    assert normalize_url("https://example.com#frag").endswith("example.com")


def test_find_emails_and_phones():
    text = "Contact us at support@example.com or +1 (555) 123-4567."
    assert "support@example.com" in find_emails(text)
    assert any("555" in p for p in find_phones(text))
