import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import load_config
from .scraper import BookScraper
from .storage import get_storage


def build_parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Books Scraper")
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Ruta config.yaml"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scrape_d = sub.add_parser("scrape", help="Scrapear y guardar")
    scrape_d.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "sqlite"],
        default=None,
        help="Override del formato (default: output.default_format del config)",
    )
    scrape_d.add_argument("--max-pages", type=int, help="Override max_pages")

    scrape_d.add_argument(
        "-n",
        "--download-images",
        action="store_true",
        help="Descargar imagenes de los libros",
    )

    scrape_d.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Hilos concurrentes para descargar imagenes",
    )

    load_d = sub.add_parser("load", help="Leer y mostrar los libros guardados")
    load_d.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "sqlite"],
        default=None,
        help="Override del formato (default: output.default_format del config)",
    )
    load_d.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cuantos libros mostrar (default: todos)",
    )

    return parser


def download_all_images(scraper, details: list, images_dir, max_workers):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(scraper.download_image, book, images_dir): book
            for book in details
        }
        for future in as_completed(futures):
            book = futures[future]
            try:
                path = future.result()
            except Exception as e:
                print(f"Error con {book.upc}: {e}")
                continue
            if path is not None:
                results.append(path)
    return results


def main():
    parser = build_parse()
    args = parser.parse_args()

    config = load_config(args.config)

    # default=None = "usar el config"; el flag solo es override explicito.
    formato = args.format or config["output"]["default_format"]

    if args.command == "load":
        storage = get_storage(formato, config)
        books = storage.load()

        total = len(books)
        if args.limit is not None:
            books = books[: args.limit]

        for book in books:
            print(f"{book['title']} | {book['price']} | {book['category']}")
        print(f"Total: {total} libros guardados")

        return 0

    # --- scrape ---

    if args.max_pages:
        config["site"]["max_pages"] = args.max_pages

    scraper = BookScraper(config)

    catalog, details = scraper.scraper_all()

    # Los datos son el producto principal: se guardan primero.
    # Si las imagenes fallan a mitad de camino, los libros ya estan en disco.
    storage = get_storage(formato, config)
    storage.save(details)

    if args.download_images:
        download_all_images(
            scraper, details, config["output"]["images_dir"], args.max_workers
        )

    print(f"Scraping completado: {len(details)} libros procesados")

    return 0


if __name__ == "__main__":
    sys.exit(main())
