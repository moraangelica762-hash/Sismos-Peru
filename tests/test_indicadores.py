import datetime as dt

import pandas as pd

from indicadores.smart import calcular_indicadores_smart


def test_indicadores_se_calculan_desde_la_evidencia():
    ahora = dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc)
    df = pd.DataFrame(
        {
            "id_usgs": ["a", "b"],
            "fecha_hora_utc": pd.to_datetime(["2026-01-01T12:00:00Z", "2026-01-01T13:00:00Z"]),
            "magnitud": [4.0, 5.0],
            "latitud": [-12.0, -13.0],
            "longitud": [-77.0, -76.0],
            "texto_utilizable": [True, True],
        }
    )
    metadata = {"ultima_sincronizacion_utc": "2026-01-01T23:00:00+00:00"}
    indicadores = calcular_indicadores_smart(df, {"silhouette": 0.4}, metadata, ahora)
    assert indicadores["Cumple"].all()
