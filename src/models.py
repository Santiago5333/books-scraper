from dataclasses import dataclass


@dataclass
class BookCatalog:
    title: str
    price: str
    availability: str
    rating: str
    book_link: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "price": self.price,
            "availability": self.availability,
            "rating": self.rating,
            "book_link": self.book_link,
        }


@dataclass
class BookDetail(BookCatalog):
    upc: str
    description: str
    category: str
    img_url: str

    def to_dict(self) -> dict:
        resultado = super().to_dict()
        resultado["upc"] = self.upc
        resultado["description"] = self.description
        resultado["category"] = self.category
        resultado["img_url"] = self.img_url
        return resultado
