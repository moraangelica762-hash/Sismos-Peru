"""
Feature engineering orientado al dashboard.

Transforma el DataFrame crudo (salida de la ingesta) en un DataFrame
enriquecido con las columnas que necesitan los gráficos: año, mes,
estación del año, década, país y departamento (región) del evento, y
categoría de profundidad. Este módulo no conoce Streamlit: solo pandas.
"""

import math
import logging

import pandas as pd

from ingesta.configuracion import ZONA_HORARIA_PERU

log = logging.getLogger("transformacion")

# -- Centroides aproximados de los departamentos de Perú (para asignar región
#    por cercanía al epicentro; enfoque simple sin depender de un servicio
#    externo de geocodificación) --------------------------------------------
DEPARTAMENTOS_PERU = {
    "Amazonas": (-6.23, -77.87),
    "Áncash": (-9.53, -77.53),
    "Apurímac": (-14.02, -72.88),
    "Arequipa": (-16.40, -71.53),
    "Ayacucho": (-13.16, -74.22),
    "Cajamarca": (-7.16, -78.50),
    "Callao": (-12.05, -77.13),
    "Cusco": (-13.53, -71.97),
    "Huancavelica": (-12.79, -74.97),
    "Huánuco": (-9.93, -76.24),
    "Ica": (-14.07, -75.73),
    "Junín": (-11.50, -75.60),
    "La Libertad": (-8.11, -79.03),
    "Lambayeque": (-6.77, -79.84),
    "Lima": (-12.05, -77.04),
    "Loreto": (-3.75, -73.25),
    "Madre de Dios": (-12.60, -69.19),
    "Moquegua": (-17.20, -70.93),
    "Pasco": (-10.68, -76.26),
    "Piura": (-5.19, -80.63),
    "Puno": (-15.84, -70.02),
    "San Martín": (-6.48, -76.37),
    "Tacna": (-18.01, -70.25),
    "Tumbes": (-3.57, -80.45),
    "Ucayali": (-8.38, -74.55),
}

# Meses del hemisferio sur -> estación (Perú está en el hemisferio sur)
MESES_A_ESTACION = {
    12: "Verano", 1: "Verano", 2: "Verano",
    3: "Otoño", 4: "Otoño", 5: "Otoño",
    6: "Invierno", 7: "Invierno", 8: "Invierno",
    9: "Primavera", 10: "Primavera", 11: "Primavera",
}

NOMBRES_MES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _distancia_haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Distancia en km entre dos puntos geográficos (fórmula de Haversine, sin dependencias externas)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def departamento_y_distancia_km(lat: float, lon: float):
    """
    Devuelve `(departamento, distancia_km)` del centroide de departamento más
    cercano al epicentro (lat, lon). La distancia se usa, por ejemplo, para
    construir una referencia de texto tipo "~40 km de Ayacucho" cuando la
    fuente de datos no trae ya una descripción de lugar (caso del IGP).
    """
    if pd.isna(lat) or pd.isna(lon):
        return "Sin dato", None
    mejor_dep, mejor_dist = None, float("inf")
    for dep, (dlat, dlon) in DEPARTAMENTOS_PERU.items():
        dist = _distancia_haversine_km(lat, lon, dlat, dlon)
        if dist < mejor_dist:
            mejor_dep, mejor_dist = dep, dist
    return mejor_dep, mejor_dist


def departamento_mas_cercano(lat: float, lon: float) -> str:
    """Asigna el departamento de Perú cuyo centroide está más cerca del epicentro (lat, lon)."""
    return departamento_y_distancia_km(lat, lon)[0]


def extraer_pais(lugar: str) -> str:
    """Extrae el país desde el texto de la USGS, p. ej. '24 km SSE of Nazca, Peru' -> 'Peru'."""
    if not isinstance(lugar, str) or "," not in lugar:
        return "Desconocido"
    return lugar.split(",")[-1].strip()


def categorizar_profundidad(profundidad_km: float) -> str:
    if pd.isna(profundidad_km):
        return None
    if profundidad_km < 70:
        return "Superficial"
    if profundidad_km < 300:
        return "Intermedio"
    return "Profundo"


def agregar_hora_local_peru(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega `fecha_hora_lima`: la misma marca de tiempo convertida a la zona
    horaria de Perú (UTC-5, sin horario de verano). El dato se sigue
    almacenando y calculando en UTC (`fecha_hora_utc`); esta columna es solo
    para MOSTRAR fechas/horas de forma intuitiva en el dashboard.
    """
    df = df.copy()
    df["fecha_hora_lima"] = df["fecha_hora_utc"].dt.tz_convert(ZONA_HORARIA_PERU)
    return df


def agregar_columnas_temporales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["anio"] = df["fecha_hora_utc"].dt.year
    df["mes"] = df["fecha_hora_utc"].dt.month
    df["nombre_mes"] = df["mes"].map(NOMBRES_MES_ES)
    df["estacion_anio"] = df["mes"].map(MESES_A_ESTACION)
    df["decada"] = (df["anio"] // 10 * 10).astype(str) + "s"
    return df


def agregar_columnas_geograficas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pais"] = df["lugar"].apply(extraer_pais)
    df["departamento"] = df.apply(
        lambda fila: departamento_mas_cercano(fila["latitud"], fila["longitud"]), axis=1
    )
    return df


def agregar_categoria_profundidad(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["categoria_profundidad"] = df["profundidad_km"].apply(categorizar_profundidad)
    return df


def transformar_sismos(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de feature engineering usado por el dashboard y el notebook."""
    log.info(f"Iniciando transformación de {len(df)} registros...")
    df = df.dropna(subset=["fecha_hora_utc", "latitud", "longitud", "magnitud"]).copy()
    df = agregar_hora_local_peru(df)
    df = agregar_columnas_temporales(df)
    df = agregar_columnas_geograficas(df)
    df = agregar_categoria_profundidad(df)
    log.info(f"Transformación completa: {df.shape[0]} filas x {df.shape[1]} columnas")
    return df
