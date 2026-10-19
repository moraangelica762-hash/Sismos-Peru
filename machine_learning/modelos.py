"""Clustering y detección de anomalías con evaluación cuantitativa.

Estos modelos describen similitudes y casos atípicos dentro del histórico.
No estiman la fecha, ubicación ni magnitud de futuros terremotos.
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


VARIABLES_MODELO = ["magnitud", "profundidad_km", "latitud", "longitud"]
SEMILLA = 42


def _matriz_modelo(df: pd.DataFrame):
    faltantes = sorted(set(VARIABLES_MODELO) - set(df.columns))
    if faltantes:
        raise ValueError(f"Faltan variables para el análisis: {', '.join(faltantes)}")
    pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    return pipeline.fit_transform(df[VARIABLES_MODELO])


def seleccionar_numero_clusters(matriz, minimo: int = 2, maximo: int = 6) -> tuple[int, dict[int, float]]:
    """Selecciona k por mayor silhouette dentro de un rango pequeño y auditable."""
    cantidad = len(matriz)
    if cantidad < 4:
        raise ValueError("Se requieren al menos 4 eventos para ejecutar clustering.")
    limite = min(maximo, cantidad - 1)
    puntajes: dict[int, float] = {}
    for k in range(minimo, limite + 1):
        etiquetas = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10).fit_predict(matriz)
        puntajes[k] = float(silhouette_score(matriz, etiquetas))
    mejor_k = max(puntajes, key=puntajes.get)
    return mejor_k, puntajes


def analizar_patrones_sismicos(
    df: pd.DataFrame,
    contaminacion: float = 0.02,
    max_filas_entrenamiento: int = 25_000,
) -> tuple[pd.DataFrame, dict]:
    """Agrupa eventos y marca atípicos, limitando el ajuste para escalar mejor."""
    if not 0 < contaminacion <= 0.1:
        raise ValueError("La contaminación debe estar entre 0 y 0.1.")
    if len(df) < 4:
        raise ValueError("Se requieren al menos 4 eventos para el análisis no supervisado.")

    resultado = df.copy()
    matriz_completa = _matriz_modelo(resultado)
    if len(resultado) > max_filas_entrenamiento:
        muestra = resultado.sample(max_filas_entrenamiento, random_state=SEMILLA).index
        posiciones = resultado.index.get_indexer(muestra)
        matriz_entrenamiento = matriz_completa[posiciones]
    else:
        matriz_entrenamiento = matriz_completa

    mejor_k, puntajes = seleccionar_numero_clusters(matriz_entrenamiento)
    clustering = KMeans(n_clusters=mejor_k, random_state=SEMILLA, n_init=10)
    clustering.fit(matriz_entrenamiento)
    resultado["cluster"] = clustering.predict(matriz_completa).astype(str)

    detector = IsolationForest(
        contamination=contaminacion,
        random_state=SEMILLA,
        n_estimators=200,
        n_jobs=-1,
    )
    detector.fit(matriz_entrenamiento)
    resultado["es_anomalia"] = detector.predict(matriz_completa) == -1
    resultado["puntaje_anomalia"] = -detector.score_samples(matriz_completa)

    metricas = {
        "eventos_analizados": int(len(resultado)),
        "eventos_entrenamiento": int(len(matriz_entrenamiento)),
        "numero_clusters": int(mejor_k),
        "silhouette": float(puntajes[mejor_k]),
        "silhouette_por_k": puntajes,
        "anomalias": int(resultado["es_anomalia"].sum()),
        "tasa_anomalias": float(resultado["es_anomalia"].mean()),
        "variables": VARIABLES_MODELO,
        "semilla": SEMILLA,
    }
    return resultado, metricas
