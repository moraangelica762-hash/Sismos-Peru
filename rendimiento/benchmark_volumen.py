"""Benchmark reproducible del pipeline con volúmenes crecientes.

Ejecutar: ``python -m rendimiento.benchmark_volumen``.
Los datos se expanden en memoria únicamente para medir transformación; el
resultado muestra tiempo y throughput, sin afirmar capacidad ilimitada.
"""

import argparse
import time

import pandas as pd

from ingesta.cliente_usgs import RUTA_PARQUET, leer_sismos_parquet
from transformacion.procesamiento import transformar_sismos


def ampliar_dataset(df: pd.DataFrame, filas: int) -> pd.DataFrame:
    if df.empty:
        raise ValueError("No se puede ampliar un dataset vacío.")
    repeticiones = (filas + len(df) - 1) // len(df)
    ampliado = pd.concat([df] * repeticiones, ignore_index=True).head(filas).copy()
    ampliado["id_usgs"] = ampliado["id_usgs"].astype(str) + "-" + ampliado.index.astype(str)
    return ampliado


def ejecutar_benchmark(volumenes: tuple[int, ...] = (10_000, 50_000, 100_000)) -> pd.DataFrame:
    base = leer_sismos_parquet(RUTA_PARQUET)
    resultados = []
    for filas in volumenes:
        muestra = ampliar_dataset(base, filas)
        inicio = time.perf_counter()
        salida = transformar_sismos(muestra)
        segundos = time.perf_counter() - inicio
        resultados.append(
            {
                "filas_entrada": filas,
                "filas_salida": len(salida),
                "segundos": round(segundos, 4),
                "filas_por_segundo": round(len(salida) / max(segundos, 1e-9), 0),
            }
        )
    return pd.DataFrame(resultados)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--volumenes", nargs="+", type=int, default=[10_000, 50_000, 100_000])
    args = parser.parse_args()
    print(ejecutar_benchmark(tuple(args.volumenes)).to_string(index=False))
