"""
Configuración central de la capa de ingesta.

Define la fuente de datos (API de la USGS), la ventana geográfica de Perú,
rutas de almacenamiento y parámetros de resiliencia de red (reintentos, timeouts).
"""

import os
from zoneinfo import ZoneInfo

# -- Zona horaria -----------------------------------------------------------
# Los datos se ALMACENAN siempre en UTC (así los entrega la API de la USGS,
# y es el estándar para datos sismológicos). 
ZONA_HORARIA_PERU = ZoneInfo("America/Lima")

# -- API USGS -------------------------------------------------------------
URL_API_USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
URL_API_USGS_COUNT = "https://earthquake.usgs.gov/fdsnws/event/1/count"

# -- IGP (Instituto Geofísico del Perú) — fuente COMPLEMENTARIA, no oficial -
# Endpoint WFS/GeoServer (no documentado públicamente por el IGP) que
# devuelve el último sismo detectado por la red sísmica nacional del Perú.
URL_IGP_ULTIMO_SISMO = (
    "https://ide.igp.gob.pe/geoserver/CTS_ultimosismo/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeName=CTS_ultimosismo:ultimo_sismo&outputFormat=application/json"
)
TIMEOUT_IGP_SEGUNDOS = 8

# Capa WFS con el listado (no solo el último) de sismos reportados por el IGP
# en lo que va del año en curso. Fuente que usa la tabla
# principal de "últimos sismos" del dashboard.
URL_IGP_SISMOS_REPORTADOS = (
    "https://ide.igp.gob.pe/geoserver/sismos_reportados/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeName=sismos_reportados:peru_igp_008_sismos_reportados"
    "&outputFormat=application/json"
)

# -- Zona geográfica que abarca Perú --------------------------------------------
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
