import numpy as np
import pandas as pd

from machine_learning.modelos import analizar_patrones_sismicos


def test_modelos_son_reproducibles_y_generan_metricas():
    rng = np.random.default_rng(7)
    cantidad = 80
    df = pd.DataFrame(
        {
            "magnitud": np.r_[rng.normal(3.5, 0.1, 40), rng.normal(6.0, 0.1, 40)],
            "profundidad_km": np.r_[rng.normal(30, 3, 40), rng.normal(180, 5, 40)],
            "latitud": rng.uniform(-18, -2, cantidad),
            "longitud": rng.uniform(-81, -69, cantidad),
        }
    )
    primera, metricas_1 = analizar_patrones_sismicos(df)
    segunda, metricas_2 = analizar_patrones_sismicos(df)
    assert primera["cluster"].equals(segunda["cluster"])
    assert primera["es_anomalia"].equals(segunda["es_anomalia"])
    assert metricas_1 == metricas_2
    assert 2 <= metricas_1["numero_clusters"] <= 6
    assert 0 < metricas_1["tasa_anomalias"] <= 0.1
