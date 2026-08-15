"""
main.py — Orquestador del proyecto.
"""

import subprocess
import sys

from ingesta.cliente_usgs import asegurar_datos_actualizados


def main() -> None:
    print("=" * 70)
    print("PROYECTO: Análisis Histórico y Alertas de Sismos en Perú")
    print("=" * 70)

    print("\n[1/2] Verificando datos de ingesta (Parquet)...")
    try:
        ruta = asegurar_datos_actualizados(horas_maximas_antiguedad=24)
        print(f"      Datos disponibles y actualizados en: {ruta}")
    except Exception as e:
        print(f"      ADVERTENCIA: no se pudo completar la ingesta/actualización ({e}).")
        print("      Si ya existe un Parquet cacheado en datos/datos_raw/, la app puede continuar igual.")

    print("\n[2/2] Iniciando Data App de Streamlit (app.py)...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])


if __name__ == "__main__":
    main()
