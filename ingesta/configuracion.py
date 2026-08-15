"""
Configuración central de la capa de ingesta.

Define la fuente de datos (API de la USGS), la ventana geográfica de Perú,
rutas de almacenamiento y parámetros de resiliencia de red (reintentos,
timeouts). El resto del proyecto importa estas constantes desde aquí para
evitar valores mágicos repetidos.
"""

import os
from zoneinfo import ZoneInfo

# -- Zona horaria -----------------------------------------------------------
# Los datos se ALMACENAN siempre en UTC (así los entrega la API de la USGS,
# y es el estándar para datos sismológicos). Esta zona horaria se usa
# únicamente para MOSTRAR fechas/horas de forma intuitiva al usuario en el
# dashboard (Perú no tiene horario de verano, por lo que el offset UTC-5 es
# fijo todo el año).
ZONA_HORARIA_PERU = ZoneInfo("America/Lima")

# -- API USGS -------------------------------------------------------------
# Todo el proyecto usa el endpoint de CONSULTA en tiempo real (`URL_API_USGS`),
# tanto para la ingesta histórica como para los datos "en vivo" (alertas y
# últimos sismos). Deliberadamente NO se usan los feeds resumen pre-generados
# de la USGS (`.../summary/2.5_day.geojson`, etc.): esos archivos los
# regenera la USGS cada varios minutos, así que pueden mostrarse
# desactualizados frente a una consulta directa a la base de datos en vivo.
URL_API_USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
URL_API_USGS_COUNT = "https://earthquake.usgs.gov/fdsnws/event/1/count"

# -- IGP (Instituto Geofísico del Perú) — fuente COMPLEMENTARIA, no oficial -
# Endpoint WFS/GeoServer (no documentado públicamente por el IGP) que
# devuelve el último sismo detectado por la red sísmica nacional del Perú.
# Es más sensible a eventos locales pequeños que la USGS, pero al no ser una
# API oficial documentada, se trata como "best effort": si falla, el
# dashboard simplemente no muestra ese widget (ver `visualizacion/componentes.py`).
URL_IGP_ULTIMO_SISMO = (
    "https://ide.igp.gob.pe/geoserver/CTS_ultimosismo/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeName=CTS_ultimosismo:ultimo_sismo&outputFormat=application/json"
)
TIMEOUT_IGP_SEGUNDOS = 8

# Capa WFS con el listado (no solo el último) de sismos reportados por el IGP
# en lo que va del año en curso. A diferencia de `URL_IGP_ULTIMO_SISMO` (que
# devuelve un único registro), esta sí permite pedir varios eventos a la vez
# (parámetros `count` y `sortBy`), por lo que es la fuente que usa la tabla
# principal de "últimos sismos" del dashboard.
URL_IGP_SISMOS_REPORTADOS = (
    "https://ide.igp.gob.pe/geoserver/sismos_reportados/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeName=sismos_reportados:peru_igp_008_sismos_reportados"
    "&outputFormat=application/json"
)

# -- Ventana geográfica de Perú --------------------------------------------
BBOX_PERU = {
    "minlatitude": -19.5,
    "maxlatitude": 0.5,
    "minlongitude": -82.0,
    "maxlongitude": -68.0,
}

CENTRO_PERU = {"latitude": -9.19, "longitude": -75.02}
RADIO_PERU_KM = 1200

# -- Parámetros de ingesta histórica ---------------------------------------
ANIOS_HISTORICO = 50  # años hacia atrás desde hoy
MAGNITUD_MINIMA_HISTORICO = 3
TIMEOUT_SEGUNDOS = 30
MAX_REINTENTOS = 4
ESPERA_BASE_SEGUNDOS = 2
ESPERA_ENTRE_PETICIONES = 1.0
LIMITE_EVENTOS_USGS = 20000

HEADERS_PETICION = {
    "User-Agent": "CIBERTEC-ProyectoAplicativo-LCD2/1.0 (uso academico; contacto: vargas.escobar.martin@gmail.com)",
    "Accept": "application/json",
}

# -- Rutas del proyecto -----------------------------------------------------
DIR_INGESTA = os.path.dirname(os.path.abspath(__file__))
DIR_BASE = os.path.dirname(DIR_INGESTA)  # raíz del proyecto

DIR_DATOS = os.path.join(DIR_BASE, "datos")
DIR_DATOS_RAW = os.path.join(DIR_DATOS, "datos_raw")
DIR_LOGS = os.path.join(DIR_BASE, "logs")

os.makedirs(DIR_DATOS_RAW, exist_ok=True)
os.makedirs(DIR_LOGS, exist_ok=True)

NOMBRE_DATASET = "sismos_peru"
RUTA_PARQUET = os.path.join(DIR_DATOS_RAW, f"{NOMBRE_DATASET}.parquet")
