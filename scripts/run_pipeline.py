"""Prepara el dataset de ventas para la API REST.

El flujo actual consiste en:
1. validar y preparar el CSV de ventas;
2. generar un dataset parquet listo para consultar;
3. dejar la API lista para servir las estadísticas.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DEFAULT_INPUT = ROOT / "data" / "ventas_completas.csv"
PARALLEL = SCRIPTS / "procesar_paralelo.py"


def python_executable() -> str:
    return sys.executable


def run_step(label: str, command: list[str]) -> None:
    print("", flush=True)
    print("=" * 80, flush=True)
    print(label, flush=True)
    print("=" * 80, flush=True)
    print(" ".join(command), flush=True)
    subprocess.check_call(command, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepara el dataset de ventas para la API REST.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--chunksize", type=int, default=100_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--executor", choices=["process", "thread"], default="thread")
    parser.add_argument("--prefix", default="", help="Prefijo opcional para las salidas de prueba.")
    return parser.parse_args()


def output_paths(prefix: str, sample: int) -> tuple[Path, Path]:
    if prefix:
        suffix = f"_{prefix}"
    elif sample and sample > 0:
        suffix = "_prueba"
    else:
        suffix = ""
    valid_path = ROOT / "data" / f"ventas_validas{suffix}.parquet"
    clean_path = ROOT / "data" / f"ventas_limpias{suffix}.parquet"
    return valid_path, clean_path


def main() -> None:
    args = parse_args()
    seed = os.environ.get("CPYD_SEED", "42")
    os.environ["CPYD_SEED"] = seed
    os.environ["PYTHONUNBUFFERED"] = "1"

    py = python_executable()
    sample = args.sample if args.sample and args.sample > 0 else 0
    valid_path, clean_path = output_paths(args.prefix, sample)

    print("Preparando dataset para la API REST", flush=True)
    print(f"Entrada: {args.input}", flush=True)
    print(f"Dataset validado: {valid_path}", flush=True)
    print(f"Dataset limpio: {clean_path}", flush=True)

    cmd_parallel = [
        py,
        str(PARALLEL),
        "--input",
        str(args.input),
        "--output",
        str(valid_path),
        "--chunksize",
        str(args.chunksize),
        "--workers",
        str(args.workers),
        "--executor",
        args.executor,
    ]
    if sample:
        cmd_parallel += ["--sample", str(sample)]
    run_step("1) Validación paralela por chunks", cmd_parallel)

    print("", flush=True)
    print("Dataset preparado para servir la API.", flush=True)


if __name__ == "__main__":
    main()
