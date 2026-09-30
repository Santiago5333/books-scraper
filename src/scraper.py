import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests as rq
from bs4 import BeautifulSoup as Bs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import load_config
from .models import BookCatalog, BookDetail


class BookScraper:
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["site"]["base_url"]
        self.catalog_path = config["site"]["catalog_path"]
        self.book_path = config["site"]["book_path"]
        self.max_pages = config["site"]["max_pages"]
        self.delay = config["site"]["request_delay"]

        # Css Selectors

        self.book_container = config["selectors"]["book_container"]
        self.title = config["selectors"]["title"]
        self.price = config["selectors"]["price"]
        self.availability = config["selectors"]["availability"]
        self.rating = config["selectors"]["rating"]
        self.book_link = config["selectors"]["book_link"]
        self.next_page = config["selectors"]["next_page"]

        # detalle del libro

        self.product_table = config["selectors"]["product_table"]
        self.upc = config["selectors"]["upc"]
        self.description = config["selectors"]["description"]
        self.category = config["selectors"]["category"]
        self.image = config["selectors"]["image"]

        self.session = self._create_session()

    def _create_session(self) -> rq.Session:
        session = rq.Session()
        retry = Retry(
            total=self.config["http"]["max_retries"],
            backoff_factor=self.config["http"]["backoff_factor"],
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": self.config["http"]["user_agent"]})
        return session

    def _get_soup(self, html: str) -> Bs:
        return Bs(html, "lxml")

    def fetch_page(self, url: str) -> str:
        timeout = (
            self.config["http"]["timeout_connect"],
            self.config["http"]["timeout_read"],
        )
        time.sleep(self.delay)
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content.decode("utf-8")

    def _text(self, element, selector: str) -> str:
        el = element.select_one(selector)

        if el is None:
            raise ValueError(f"No se encontró elemento con selector: {selector}")
        return el.get_text(strip=True)

    def _attr(self, element, selector: str, attr: str) -> str:
        el = element.select_one(selector)

        if el is None:
            raise ValueError(f"No se encontró elemento con selector: {selector}")
        value = el.get(attr)
        if isinstance(value, list):
            value = value[0] if value else ""
        return value or ""

    def parse_catalog(self, html: str) -> list[BookCatalog]:
        soup = self._get_soup(html)
        catalog = []

        for q in soup.select(self.book_container):
            title_el = self._text(q, self.title)

            price_el = self._text(q, self.price)

            availability_el = self._text(q, self.availability)

            cls_tag = q.select_one(self.rating)
            cls = cls_tag.get("class") if cls_tag else None
            rating_el = cls[1] if cls and len(cls) > 1 else ""

            book_link_raw = self._attr(q, self.book_link, "href")
            book_link_el = urljoin(self.catalog_path, book_link_raw).lstrip("/")

            catalog.append(
                BookCatalog(
                    title=title_el,
                    price=price_el,
                    availability=availability_el,
                    rating=rating_el,
                    book_link=book_link_el,
                )
            )
        return catalog

    def parse_detail(
        self,
        book_relative_url: str,
        data_catalog: BookCatalog,
        html: str | None = None,
    ) -> BookDetail:
        # Si html viene, usar ese (sin red). Si viene None, traer por red
        book_path = urljoin(self.base_url, book_relative_url)

        if html is not None:
            soup = self._get_soup(html)

        if html is None:
            html = self.fetch_page(book_path)
            soup = self._get_soup(html)

        upc_el = self._text(soup, self.upc)

        description_el = self._text(soup, self.description)

        category_el = self._text(soup, self.category)

        img_src = self._attr(soup, self.image, "src")

        title_el = data_catalog.title
        price_el = data_catalog.price
        availability_el = data_catalog.availability
        rating_el = data_catalog.rating
        book_link_el = data_catalog.book_link
        img_url_absoluta = urljoin(self.base_url, img_src)

        return BookDetail(
            title=title_el,
            price=price_el,
            availability=availability_el,
            rating=rating_el,
            book_link=book_link_el,
            upc=upc_el,
            description=description_el,
            category=category_el,
            img_url=img_url_absoluta,
        )

    def download_image(self, data_book: BookDetail, images_dir):

        images_dir = Path(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        upc = data_book.upc
        url = data_book.img_url

        if not upc or not url:
            print(f"Falta datos para descargar imagen: upc:{upc}, url:{url}")
            return None

        ext = os.path.splitext(url)[1] or ".jpg"
        filename = f"{upc}{ext}"
        file_path = images_dir / filename

        if file_path.exists():
            return file_path

        try:
            response = self.session.get(
                url,
                timeout=(
                    self.config["http"]["timeout_connect"],
                    self.config["http"]["timeout_read"],
                ),
            )
            response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        except rq.RequestException as e:
            print(f"Error descargando imagen para UPC {upc}: {e}")
            return None

    def scraper_all(self) -> tuple[list[BookCatalog], list[BookDetail]]:
        all_catalog = []
        all_detaills = []
        page = 1
        seen_book_link = set()

        while True:
            if self.max_pages and page > self.max_pages:
                break

            url = self.base_url + self.catalog_path.format(page_num=page)
            html = self.fetch_page(url)
            catalog = self.parse_catalog(html)

            if not catalog:
                break

            all_catalog.extend(catalog)

            for catalog_item in catalog:
                if catalog_item.book_link not in seen_book_link:
                    seen_book_link.add(catalog_item.book_link)
                    book_url = urljoin(self.base_url, catalog_item.book_link)
                    html_detail = self.fetch_page(book_url)
                    detail = self.parse_detail(
                        catalog_item.book_link, catalog_item, html_detail
                    )
                    all_detaills.append(detail)
            page += 1

        return all_catalog, all_detaills
