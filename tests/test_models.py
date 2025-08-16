from app.schemas import BrandContext, Product


def test_brand_context_model():
    bc = BrandContext(site_url="https://example.com", products=[Product(title="Tee")])
    assert bc.site_url == "https://example.com"
    assert bc.products[0].title == "Tee"
