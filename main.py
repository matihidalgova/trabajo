"""Punto de entrada de la API REST de estadísticas de ventas."""

from pathlib import Path

import uvicorn

from scripts.api_service import bootstrap_dataset
from scripts.api import app

ROOT = Path(__file__).resolve().parent


def main() -> None:
    bootstrap_dataset()
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
