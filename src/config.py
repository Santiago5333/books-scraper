from pathlib import Path
from typing import Any

import yaml


def load_config(ruta: str) -> dict[str, Any]:
    path = Path(ruta).resolve()
    try:
        with open(path, "r", encoding="utf-8") as archivo:
            datos = yaml.safe_load(archivo)
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró la ruta: {ruta}")
    except yaml.YAMLError:
        raise yaml.YAMLError
    return datos
