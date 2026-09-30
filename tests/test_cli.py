"""Smoke del CLI: build_parse() construye y los flags parsean bien.

Alcance: SOLO el parser. main() hace red (scrape) y disco (save/load),
así que no se toca acá — se smokea aparte con:
    python3 -m src.cli scrape --max-pages 1
    python3 -m src.cli load --limit 3

Contrato clave codificado acá: --format con default=None significa
"usar output.default_format del config" (Camino A). Si alguien vuelve
a ponerle default="json" al flag, test_scrape_defaults_usan_config
queda en rojo: dos fuentes de verdad.
"""

from argparse import ArgumentParser

import pytest

from src.cli import build_parse


def test_build_parse_construye():
    # Smoke minimo: codigo nuevo jamas ejecutado = verificado por nadie.
    parser = build_parse()
    assert isinstance(parser, ArgumentParser)


def test_scrape_defaults_usan_config():
    # Sin flags: TODO en None/False, el config manda.
    ns = build_parse().parse_args(["scrape"])
    assert ns.command == "scrape"
    assert ns.format is None  # default=None = "usar el config"
    assert ns.max_pages is None
    assert ns.download_images is False
    assert ns.max_workers == 8


def test_scrape_flags_cortos_override():
    ns = build_parse().parse_args(["scrape", "-f", "csv", "-n"])
    assert ns.format == "csv"
    assert ns.download_images is True


def test_scrape_flags_largos_override():
    ns = build_parse().parse_args(
        ["scrape", "--format", "sqlite", "--max-pages", "3",
         "--download-images", "--max-workers", "4"]
    )
    assert ns.format == "sqlite"
    assert ns.max_pages == 3
    assert ns.download_images is True
    assert ns.max_workers == 4


def test_load_defaults_usan_config():
    ns = build_parse().parse_args(["load"])
    assert ns.command == "load"
    assert ns.format is None  # mismo patron que scrape
    assert ns.limit is None  # None = mostrar todos


def test_load_flags_override():
    ns = build_parse().parse_args(["load", "-f", "csv", "--limit", "5"])
    assert ns.format == "csv"
    assert ns.limit == 5


def test_config_global_antes_del_subcomando():
    # -c es del parser raiz: va ANTES del subcomando scrape.
    ns = build_parse().parse_args(["-c", "otro.yaml", "scrape"])
    assert ns.config == "otro.yaml"


def test_formato_invalido_rechazado_en_parseo():
    # choices=["json","csv","sqlite"]: argparse rechaza "xml" ANTES de
    # llegar a get_storage. Sale con codigo 2 (error de uso).
    with pytest.raises(SystemExit) as excinfo:
        build_parse().parse_args(["scrape", "-f", "xml"])
    assert excinfo.value.code == 2


def test_subcomando_requerido():
    # required=True: sin subcomando no hay namespace que inspeccionar.
    with pytest.raises(SystemExit) as excinfo:
        build_parse().parse_args([])
    assert excinfo.value.code == 2
