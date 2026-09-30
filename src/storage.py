import csv
import json
import sqlite3 as sql
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .models import BookDetail


class Storage(ABC):
    def __init__(self, config: dict):
        self.config = config

    def _to_dicts(self, books: list):
        dicts = []
        for book in books:
            if hasattr(book, "to_dict"):
                dicts.append(book.to_dict())
            else:
                dicts.append(book)
        return dicts

    @abstractmethod
    def save(self, books: List[BookDetail]) -> None:
        pass

    @abstractmethod
    def load(self) -> list[dict]:
        pass


class JSONStorage(Storage):
    def __init__(self, config: dict):
        super().__init__(config)
        self.path = Path(config["output"]["json_path"])

    def save(self, books: List[BookDetail]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = self._to_dicts(books)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def load(self) -> list[dict]:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []


class CSVStorage(Storage):
    def __init__(self, config: dict):
        super().__init__(config)
        self.path = Path(config["output"]["csv_path"])
        self.delimiter = config["output"]["csv_delimiter"]

    def save(self, books: List[BookDetail]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = self._to_dicts(books)

        with open(self.path, "w", encoding="utf-8", newline="") as file:
            if not data:
                # save([]): el archivo ya quedo creado y vacio por open("w"),
                # y DictReader sobre un archivo vacio devuelve [].
                return

            fieldnames = data[0].keys()
            write = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
            )
            write.writeheader()
            write.writerows(data)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []

        with open(self.path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            rows = list(reader)

        return rows


class SQLITEStorage(Storage):
    def __init__(self, config: dict):
        super().__init__(config)
        self.path = Path(config["output"]["sqlite_path"])

    def save(self, books: List[BookDetail]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with sql.connect(self.path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                                     CREATE TABLE IF NOT EXISTS books(
                                     title TEXT ,
                                     price TEXT ,
                                     availability TEXT ,
                                     rating TEXT ,
                                     book_link TEXT ,
                                     upc TEXT ,
                                     description TEXT,
                                     category TEXT,
                                     img_url TEXT
                                     )
                                     """)
            cursor.execute("DELETE FROM books")
            data = self._to_dicts(books)

            cursor.executemany(
                """INSERT INTO books(title, price, availability, rating,
                               book_link, upc, description, category, img_url)
                               VALUES (:title, :price, :availability, :rating,
                               :book_link, :upc, :description, :category, :img_url)""",
                data,
            )

        conn.close()

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []

        with sql.connect(self.path) as conn:
            conn.row_factory = sql.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM books")
            rows = cursor.fetchall()
            data = [dict(row) for row in rows]

        conn.close()
        return data


def get_storage(format: str, config: dict) -> Storage:
    storages = {"json": JSONStorage, "csv": CSVStorage, "sqlite": SQLITEStorage}
    format_key = format.lower()

    if format_key not in storages:
        raise ValueError(
            f"Formato de almacenamiento desconocido: {format}."
            f"Opciones válidas: {','.join(storages.keys())}"
        )

    return storages[format_key](config)
