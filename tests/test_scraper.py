import os
import sys

# Ensure we can import from src as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import BookCatalog, BookDetail
from src.scraper import BookScraper


def load_fixture(filename):
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_parse_catalog():
    html = load_fixture("page1.html")
    # Minimal config matching config.yaml
    config = {
        "site": {
            "base_url": "https://books.toscrape.com",
            "catalog_path": "/catalogue/page-{page_num}.html",
            "book_path": "/catalogue/{slug}",
            "max_pages": 0,
            "request_delay": 0,
        },
        "selectors": {
            "book_container": "article.product_pod",
            "title": "h3 a",
            "price": ".price_color",
            "availability": ".availability",
            "rating": ".star-rating",
            "book_link": "h3 a",
            "next_page": ".next a",
            "product_table": "table.table-striped tr",
            "upc": "td",
            "description": "#product_description + p",
            "category": ".breadcrumb li:nth-child(3) a",
            "image": "#product_gallery img",
        },
        "http": {
            "timeout_connect": 5,
            "timeout_read": 15,
            "user_agent": "test-agent",
            "max_retries": 1,
            "backoff_factor": 0,
        },
    }
    scraper = BookScraper(config)
    catalog = scraper.parse_catalog(html)
    assert len(catalog) == 2
    # First book
    assert catalog[0].title == "A Light in the Attic"
    assert catalog[0].price == "£51.77"
    assert "In stock" in catalog[0].availability
    assert catalog[0].rating == "Three"
    assert catalog[0].book_link == "catalogue/a-light-in-the-attic_1000/index.html"
    # Second book
    assert catalog[1].title == "Tipping the Velvet"
    assert catalog[1].price == "£53.74"
    assert "In stock" in catalog[1].availability
    assert catalog[1].rating == "One"
    assert catalog[1].book_link == "catalogue/tipping-the-velvet_999/index.html"


def test_parse_detail():
    html = load_fixture("book-detail-example.html")
    config = {
        "site": {
            "base_url": "https://books.toscrape.com",
            "catalog_path": "/catalogue/page-{page_num}.html",
            "book_path": "/catalogue/{slug}",
            "max_pages": 0,
            "request_delay": 0,
        },
        "selectors": {
            "book_container": "article.product_pod",
            "title": "h3 a",
            "price": ".price_color",
            "availability": ".availability",
            "rating": ".star-rating",
            "book_link": "h3 a",
            "next_page": ".next a",
            "product_table": "table.table-striped tr",
            "upc": "td",
            "description": "#product_description + p",
            "category": ".breadcrumb li:nth-child(3) a",
            "image": "#product_gallery img",
        },
        "http": {
            "timeout_connect": 5,
            "timeout_read": 15,
            "user_agent": "test-agent",
            "max_retries": 1,
            "backoff_factor": 0,
        },
    }
    scraper = BookScraper(config)
    # Create a dummy BookCatalog for the book (as would be obtained from catalog)
    catalog_item = BookCatalog(
        title="A Light in the Attic",
        price="£51.77",
        availability="In stock",
        rating="Three",
        book_link="catalogue/a-light-in-the-attic_1000/index.html",
    )
    detail = scraper.parse_detail(
        "catalogue/a-light-in-the-attic_1000/index.html",
        catalog_item,
        html=html,
    )
    assert isinstance(detail, BookDetail)
    assert detail.title == "A Light in the Attic"
    assert detail.price == "£51.77"
    assert detail.availability == "In stock"
    assert detail.rating == "Three"
    assert detail.book_link == "catalogue/a-light-in-the-attic_1000/index.html"
    assert detail.upc == "a58914f0743b7d1e"
    # Description es el texto del <p> (el blurb real del libro), no el heading
    assert "a hard to imagine" in detail.description
    assert detail.category == "Travel"
    # Image URL should be absolute
    assert detail.img_url.startswith("https://books.toscrape.com/media/cache/")

