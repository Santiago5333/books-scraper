import os
import sys

# Ensure we can import from src as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.storage import CSVStorage, JSONStorage, SQLITEStorage, get_storage


def make_full_config(tmp_path):
    """Config completo de output: los 3 paths + claves de todos los formatos.

    Camino A: el formato llega como ARGUMENTO, no se lee del config;
    default_format queda en el config para que main() haga el fallback.
    Cada subclase solo lee SU clave, pero tener todas evita que un
    cambio futuro en __init__ rompa tests del despachador.
    """
    return {
        "output": {
            "default_format": "json",
            "json_path": str(tmp_path / "books.json"),
            "csv_path": str(tmp_path / "books.csv"),
            "csv_delimiter": ";",
            "sqlite_path": str(tmp_path / "books.db"),
        }
    }


def test_get_storage_returns_json(tmp_path):
    store = get_storage("json", make_full_config(tmp_path))
    assert isinstance(store, JSONStorage)


def test_get_storage_returns_csv(tmp_path):
    store = get_storage("csv", make_full_config(tmp_path))
    assert isinstance(store, CSVStorage)


def test_get_storage_returns_sqlite(tmp_path):
    store = get_storage("sqlite", make_full_config(tmp_path))
    assert isinstance(store, SQLITEStorage)


def test_get_storage_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError, match="xml"):
        get_storage("xml", make_full_config(tmp_path))


def test_get_storage_case_insensitive(tmp_path):
    # El formato puede venir del flag o del config:
    # "JSON" debe despachar igual que "json".
    store = get_storage("JSON", make_full_config(tmp_path))
    assert isinstance(store, JSONStorage)
