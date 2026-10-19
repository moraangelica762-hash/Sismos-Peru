import pandas as pd

from ingesta.cliente_usgs import normalizar_sismos


def test_normalizacion_por_lotes_no_pierde_eventos():
    features = [
        {
            "id": f"evento-{i}",
            "properties": {"time": 1_700_000_000_000 + i, "mag": 4.0, "place": "Peru"},
            "geometry": {"coordinates": [-77.0, -12.0, 40.0]},
        }
        for i in range(7)
    ]
    salida = normalizar_sismos(features, tamano_lote=3)
    assert len(salida) == 7
    assert salida["id_usgs"].is_unique
    assert isinstance(salida["fecha_hora_utc"].dtype, pd.DatetimeTZDtype)
