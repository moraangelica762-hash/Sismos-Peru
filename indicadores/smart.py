"""Cálculo de indicadores SMART a partir de evidencia observable."""

import datetime as dt

import pandas as pd


COLUMNAS_CRITICAS = ["id_usgs", "fecha_hora_utc", "magnitud", "latitud", "longitud"]


def calcular_indicadores_smart(
    df: pd.DataFrame,
    metricas_ml: dict | None = None,
    metadata_ingesta: dict | None = None,
    ahora_utc: dt.datetime | None = None,
) -> pd.DataFrame:
    ahora_utc = ahora_utc or dt.datetime.now(dt.timezone.utc)
    completitud = 100 * (1 - df[COLUMNAS_CRITICAS].isna().any(axis=1).mean())
    duplicados = int(df["id_usgs"].duplicated().sum())
    cobertura_texto = 100 * float(df.get("texto_utilizable", pd.Series(False, index=df.index)).mean())
    fecha_sync = None if not metadata_ingesta else metadata_ingesta.get("ultima_sincronizacion_utc")
    ultima_sync = pd.to_datetime(fecha_sync, utc=True, errors="coerce")
    frescura_horas = None
    if pd.notna(ultima_sync):
        frescura_horas = max(0.0, (ahora_utc - ultima_sync.to_pydatetime()).total_seconds() / 3600)
    silhouette = None if not metricas_ml else metricas_ml.get("silhouette")

    filas = [
        {
            "Indicador": "Calidad de datos críticos",
            "Definición medible": "% de filas sin nulos en ID, fecha, magnitud y coordenadas",
            "Meta": ">= 95%",
            "Resultado": f"{completitud:.2f}%",
            "Cumple": completitud >= 95,
            "Horizonte": "En cada actualización",
        },
        {
            "Indicador": "Unicidad del histórico",
            "Definición medible": "IDs USGS duplicados después de la fusión incremental",
            "Meta": "0 duplicados",
            "Resultado": str(duplicados),
            "Cumple": duplicados == 0,
            "Horizonte": "En cada actualización",
        },
        {
            "Indicador": "Frescura operativa",
            "Definición medible": "Horas desde la última consulta exitosa a USGS",
            "Meta": "<= 48 horas",
            "Resultado": "Sin evidencia" if frescura_horas is None else f"{frescura_horas:.1f} h",
            "Cumple": frescura_horas is not None and frescura_horas <= 48,
            "Horizonte": "Revisión diaria",
        },
        {
            "Indicador": "Cobertura de texto",
            "Definición medible": "% de descripciones con al menos dos tokens útiles",
            "Meta": ">= 90%",
            "Resultado": f"{cobertura_texto:.2f}%",
            "Cumple": cobertura_texto >= 90,
            "Horizonte": "En cada actualización",
        },
        {
            "Indicador": "Separación de clusters",
            "Definición medible": "Coeficiente silhouette del k seleccionado",
            "Meta": ">= 0.20",
            "Resultado": "No calculado" if silhouette is None else f"{silhouette:.3f}",
            "Cumple": silhouette is not None and silhouette >= 0.20,
            "Horizonte": "En cada ejecución del modelo",
        },
    ]
    return pd.DataFrame(filas)
