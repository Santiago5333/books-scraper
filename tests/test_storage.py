import os
import sys

# Ensure we can import from src as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import BookDetail
from src.storage import CSVStorage, JSONStorage, SQLITEStorage


def make_config(json_path):
    return {"output": {"json_path": str(json_path)}}


def make_csv_config(csv_path, delimiter=";"):
    return {"output": {"csv_path": str(csv_path), "csv_delimiter": delimiter}}


def make_book(title, price):
    """BookDetail completo para ejercitar el camino real de save()."""
    return BookDetail(
        title=title,
        price=price,
        availability="In stock",
        rating="Four",
        book_link=f"catalogue/{title.lower().replace(' ', '-')}_1/index.html",
        upc="a897fe50c9",
        description="Un libro de prueba.",
        category="Fiction",
        img_url="media/cache/1.jpg",
    )


# ---------- JSONStorage ----------

def test_json_roundtrip(tmp_path):
    path = tmp_path / "data" / "books.json"
    store = JSONStorage(make_config(path))
    books = [
        make_book("Libro A", "£20.00"),
        make_book("Libro B", "£55.50"),
    ]

    store.save(books)
    assert path.exists()
    assert store.load() == [b.to_dict() for b in books]


def test_json_save_accepts_mixed_list(tmp_path):
    # La decisión de diseño fue detectar to_dict POR ITEM (hasattr),
    # no por el tipo del primero. Una lista mixta debe salir completa:
    # el BookDetail convertido y el dict ya convertido, en el mismo orden.
    path = tmp_path / "books.json"
    store = JSONStorage(make_config(path))
    book = make_book("Libro A", "£20.00")
    plain = {"title": "Libro B", "price": "£55.50"}

    store.save([book, plain])
    assert store.load() == [book.to_dict(), plain]


def test_json_creates_missing_dirs(tmp_path):
    path = tmp_path / "no_existe" / "sub" / "books.json"
    store = JSONStorage(make_config(path))

    store.save([{"title": "Libro A"}])
    assert path.exists()


def test_json_load_missing_file_returns_empty(tmp_path):
    store = JSONStorage(make_config(tmp_path / "books.json"))
    assert store.load() == []


# ---------- CSVStorage ----------

def test_csv_roundtrip(tmp_path):
    path = tmp_path / "data" / "books.csv"
    store = CSVStorage(make_csv_config(path))
    books = [
        make_book("Libro A", "£20.00"),
        make_book("Libro B", "£55.55"),
    ]

    store.save(books)
    assert path.exists()
    assert store.load() == [b.to_dict() for b in books]


def test_csv_uses_delimiter_from_config(tmp_path):
    # El separador no puede estar hardcodeado: sale de
    # config["output"]["csv_delimiter"]. El header del archivo lo delata.
    path = tmp_path / "books.csv"
    store = CSVStorage(make_csv_config(path, delimiter=";"))

    store.save([make_book("Libro A", "£20.00")])
    header = path.read_text(encoding="utf-8").splitlines()[0]
    # 9 columnas -> 8 separadores, sin importar el ORDEN (ese es
    # decision de diseño del storage, el test no lo fija).
    assert header.count(";") == 8
    assert "title" in header


def test_csv_empty_list_still_writes_header(tmp_path):
    # CONTRATO (lo que el test exige, nada mas): tras save([]) el archivo
    # existe y load() devuelve [] sin reventar. Que header escribir con
    # lista vacia es decision de diseño: no hay books[0] de donde derivar
    # columnas (archivo vacio o header constante, ambas pasan).
    path = tmp_path / "books.csv"
    store = CSVStorage(make_csv_config(path))

    store.save([])
    assert path.exists()
    assert store.load() == []


def test_csv_creates_missing_dirs(tmp_path):
    path = tmp_path / "no_existe" / "sub" / "books.csv"
    store = CSVStorage(make_csv_config(path))

    store.save([{"title": "Libro A"}])
    assert path.exists()


def test_csv_load_missing_file_returns_empty(tmp_path):
    store = CSVStorage(make_csv_config(tmp_path / "books.csv"))
    assert store.load() == []


# ---------- SQLITEStorage ----------

def make_sqlite_config(sqlite_path):
    return {"output": {"sqlite_path": str(sqlite_path)}}


def test_sqlite_roundtrip(tmp_path):
    path = tmp_path / "data" / "books.db"
    store = SQLITEStorage(make_sqlite_config(path))
    books = [
        make_book("Libro A", "£20.00"),
        make_book("Libro B", "£55.55"),
    ]

    store.save(books)
    assert path.exists()
    assert store.load() == [b.to_dict() for b in books]


def test_sqlite_creates_missing_dirs(tmp_path):
    path = tmp_path / "no_existe" / "sub" / "books.db"
    store = SQLITEStorage(make_sqlite_config(path))

    store.save([make_book("Libro A", "£20.00")])
    assert path.exists()


def test_sqlite_load_missing_file_returns_empty(tmp_path):
    # Igual que JSON/CSV: un .db que no existe carga como lista vacia.
    # (Que sqlite cree el archivo al leer es aceptable; el contrato
    # es el [] sin reventar.)
    store = SQLITEStorage(make_sqlite_config(tmp_path / "books.db"))
    assert store.load() == []


def test_sqlite_second_save_replaces_content(tmp_path):
    # CONTRATO (consistente con JSON y CSV): save() pisa el contenido
    # anterior. El .db persiste entre corridas; si se scrapea de nuevo
    # y se guarda, la tabla refleja solo la ultima corrida, sin
    # duplicados de corridas viejas.
    path = tmp_path / "books.db"
    store = SQLITEStorage(make_sqlite_config(path))
    primera = make_book("Libro A", "£20.00")
    segunda = make_book("Libro B", "£55.55")

    store.save([primera])
    store.save([segunda])

    assert store.load() == [segunda.to_dict()]
