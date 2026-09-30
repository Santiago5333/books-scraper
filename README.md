# books-scraper

Scraper de [books.toscrape.com](https://books.toscrape.com) escrito en Python
(requests + BeautifulSoup), con CLI, tres formatos de almacenamiento y descarga
de imágenes.

Proyecto de aprendizaje: estructura de código, tests, y un pipeline real de
scraping de punta a punta.

## Estructura

    books-scraper/
    ├── config.yaml          # Configuración (URLs, selectores, HTTP, salidas)
    ├── requirements.txt
    ├── src/
    │   ├── config.py        # load_config(): lee el YAML
    │   ├── models.py        # BookCatalog, BookDetail (dataclasses)
    │   ├── scraper.py       # BookScraper: fetch, parse, dedupe, imágenes
    │   ├── storage.py       # Storage ABC + JSON/CSV/SQLite + despachador
    │   └── cli.py           # argparse: subcomandos scrape y load
    ├── tests/               # 32 tests (pytest) + fixtures de HTML
    └── data/                # Salida: books.json, books.csv, books.db, images/

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Uso

Scrapear el sitio y guardar (formato del config, JSON por defecto):

    python3 -m src.cli scrape

Con opciones:

    python3 -m src.cli scrape --max-pages 2          # limitar páginas
    python3 -m src.cli scrape -f csv                 # forzar formato
    python3 -m src.cli scrape -n                     # descargar imágenes
    python3 -m src.cli scrape -n --max-workers 4     # hilos de descarga
    python3 -m src.cli -c otro.yaml scrape           # otro config

Leer lo guardado:

    python3 -m src.cli load
    python3 -m src.cli load -f csv --limit 5

Flags con default `None` = "usar el valor del config"; pasar el flag es
siempre un override explícito. `max_pages: 0` en el config significa
scrapear hasta que se acaben las páginas (el sitio tiene 50).

## Configuración (config.yaml)

- `site`: URLs (`base_url`, `catalog_path` con `{page_num}`, `book_path`),
  `max_pages`, `request_delay` (cortesía entre requests, en segundos).
- `selectors`: selectores CSS para catálogo y página de detalle. Si el
  sitio cambia, se actualizan acá sin tocar código.
- `http`: timeouts (connect/read), User-Agent, reintentos con backoff
  (montados en un `requests.Session` con `HTTPAdapter`).
- `output`: `default_format`, rutas de salida por formato,
  `csv_delimiter` y `images_dir`.

## Datos capturados

Por libro: título, precio, disponibilidad, rating, link, UPC, descripción,
categoría e imagen. Cada formato guarda lo mismo (`save()` pisa el contenido
anterior; `load()` devuelve lista de dicts).

Notas del sitio:

- 20 libros por página, 50 páginas (1000 libros).
- Las imágenes se guardan en `data/images/` con el UPC como nombre
  (`{upc}.jpg`). Si ya existe, no se re-descarga (caché).
- El dedupe entre páginas usa el `book_link` normalizado, así que un libro
  repetido no se procesa dos veces.
- Tres libros del sitio tienen breadcrumb incompleto y quedan con
  categoría "Default": es un dato del sitio, no un bug del scraper.

## Tests

    source .venv/bin/activate
    python3 -m pytest -q

32 tests: scraper (2), storage JSON/CSV/SQLite (13), despachador (5),
imágenes (3), CLI (9). Los fixtures de HTML imitan la estructura real del
sitio; ningún test toca la red.

## Decisiones de diseño

- **Fetch separado de parse**: los métodos de parseo reciben HTML, no lo
  piden. Se testean con fixtures sin red.
- **Una fuente de verdad por dato**: el catálogo se parsea una vez y el
  resto del pipeline itera ese resultado; el despachador de storage recibe
  el formato explícito (`get_storage(format, config)`) y el CLI resuelve
  el default del config.
- **Datos antes que archivos**: el `save()` corre antes de descargar
  imágenes; si la descarga falla a mitad de camino, los libros ya quedaron.
- **Errores ruidosos**: falta de clave en el config o selector que no
  encuentra elemento revientan con mensaje claro, en vez de devolver
  defaults que esconden el problema.
