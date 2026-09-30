"""Tests del downloader de imágenes de BookScraper.

El método bajo test descarga imágenes usando la sesión del scraper,
así que mockeamos session.get para no pegar a la red.

OJO: config.output.images_dir apunta a un dir DISTINTO del images_dir
que los tests pasan como parámetro. Si el método escribe en el del
config, los asserts fallan: el contrato es que el parámetro manda.
"""

from src.models import BookDetail
from src.scraper import BookScraper


FAKE_PNG = b"\x89PNG fake bytes"

IMG_URL = "https://books.toscrape.com/media/cache/example.jpg"


def _book(upc="a1b2c3", img_url=IMG_URL):
    """BookDetail mínimo con lo que usa el downloader."""
    return BookDetail(
        title="Libro test",
        price="£10",
        availability="In stock",
        rating="Three",
        book_link="https://books.toscrape.com/catalogue/x_999/index.html",
        upc=upc,
        description="desc",
        category="Fiction",
        img_url=img_url,
    )


def _scraper(tmp_path, responses=()):
    """BookScraper con config mínima válida y sesión falsa inyectada."""
    config = {
        "site": {
            "base_url": "https://books.toscrape.com/",
            "catalog_path": "catalogue/page-{page_num}.html",
            "book_path": "catalogue/",
            "max_pages": 1,
            "request_delay": 0,
        },
        "selectors": {
            key: "x"
            for key in (
                "book_container",
                "title",
                "price",
                "availability",
                "rating",
                "book_link",
                "next_page",
                "product_table",
                "upc",
                "description",
                "category",
                "image",
            )
        },
        "http": {
            "max_retries": 0,
            "backoff_factor": 0,
            "user_agent": "test-agent",
            "timeout_connect": 5,
            "timeout_read": 15,
        },
        "output": {
            "images_dir": str(tmp_path / "config_images"),
        },
    }
    scraper = BookScraper(config)
    scraper.session = _FakeSession(list(responses))
    return scraper


class _FakeResponse:
    """Se comporta como la parte de requests.Response que usa el downloader."""

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        """La respuesta fake siempre es 200 OK."""
        return None


class _FakeSession:
    """Reemplaza requests.Session en el scraper: graba las URLs pedidas."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        if self._responses:
            return self._responses.pop(0)
        # Sin respuestas canned: responde genérico (como session real).
        return _FakeResponse(b"")


class TestDescargaImagenes:
    def test_guarda_imagen_con_nombre_upc_y_extension(self, tmp_path):
        scraper = _scraper(tmp_path, responses=[_FakeResponse(FAKE_PNG)])
        images_dir = tmp_path / "images"

        scraper.download_image(_book(), images_dir)

        expected = images_dir / "a1b2c3.jpg"
        assert expected.exists()
        assert expected.read_bytes() == FAKE_PNG

    def test_crea_images_dir_si_no_existe(self, tmp_path):
        # dir padre tampoco existe
        images_dir = tmp_path / "data" / "images"

        scraper = _scraper(tmp_path, responses=[_FakeResponse(FAKE_PNG)])
        scraper.download_image(_book(), images_dir)

        assert images_dir.exists()

    def test_consulta_la_url_del_libro(self, tmp_path):
        scraper = _scraper(tmp_path)

        scraper.download_image(_book(), images_dir=tmp_path / "images")

        assert scraper.session.urls == [IMG_URL]
