"""Esquemas Pandera para validar tipos, unicidad y rangos de los datos sísmicos."""

import pandera as pa
from pandera import Column, Check, DataFrameSchema

# -- Rango geográfico de Perú y zona fronteriza cubierta por el bbox de ingesta
LAT_MIN, LAT_MAX = -20.0, 1.0
LON_MIN, LON_MAX = -83.0, -67.0

esquema_sismos_crudos = DataFrameSchema(
    {
        "id_usgs": Column(str, Check.str_length(min_value=1), unique=True, nullable=False),
        "fecha_hora_utc": Column("datetime64[ns, UTC]", nullable=False),
        "magnitud": Column(float, Check.in_range(0, 10), nullable=False),
        "tipo_magnitud": Column(str, nullable=True),
        "lugar": Column(str, nullable=True),
        "profundidad_km": Column(float, Check.in_range(-10, 800), nullable=True),
        "longitud": Column(float, Check.in_range(LON_MIN, LON_MAX), nullable=False),
        "latitud": Column(float, Check.in_range(LAT_MIN, LAT_MAX), nullable=False),
        "alerta_tsunami": Column(int, Check.isin([0, 1]), nullable=True, coerce=True),
        "significancia": Column(float, nullable=True, coerce=True),
        "num_estaciones": Column(float, nullable=True),
        "gap_azimutal": Column(float, nullable=True),
        "rms": Column(float, nullable=True),
        "estado_revision": Column(str, nullable=True),
        "tipo_evento": Column(str, nullable=True),
        "url_detalle": Column(str, nullable=True),
    },
    strict=False,  # permite columnas adicionales derivadas río abajo
    coerce=True,
)

esquema_sismos_enriquecidos = esquema_sismos_crudos.add_columns(
    {
        "anio": Column(int, Check.in_range(1900, 2100), nullable=False, coerce=True),
        "mes": Column(int, Check.in_range(1, 12), nullable=False, coerce=True),
        "nombre_mes": Column(str, nullable=False),
        "estacion_anio": Column(
            str, Check.isin(["Verano", "Otoño", "Invierno", "Primavera"]), nullable=False
        ),
        "decada": Column(str, nullable=False),
        "fecha_hora_lima": Column("datetime64[ns, America/Lima]", nullable=False),
        "pais": Column(str, nullable=False),
        "departamento": Column(str, nullable=False),
        "categoria_profundidad": Column(
            str, Check.isin(["Superficial", "Intermedio", "Profundo"]), nullable=True
        ),
    }
)


def validar_sismos_crudos(df):
    """Valida el DataFrame recién normalizado desde la API/Parquet. Lanza SchemaError si falla."""
    return esquema_sismos_crudos.validate(df, lazy=True)


def validar_sismos_enriquecidos(df):
    """Valida el DataFrame ya transformado (con features) que consume el dashboard."""
    return esquema_sismos_enriquecidos.validate(df, lazy=True)
