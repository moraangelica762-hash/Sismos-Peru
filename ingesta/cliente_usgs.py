"""
Cliente de ingesta para la API de la USGS.

Responsabilidad única: descargar, normalizar y cachear en Parquet los sismos
históricos de Perú. Incluye manejo de errores de red con reintentos.

"""

import datetime
import json
import logging
import os
import sys
import time

import pandas as pd
import pyarrow.parquet as pq
import requests

from ingesta.configuracion import (
    BBOX_PERU,
    DIR_DATOS_RAW,
    DIR_LOGS,
    ESPERA_BASE_SEGUNDOS,
    ESPERA_ENTRE_PETICIONES,
    HEADERS_PETICION,
    LIMITE_EVENTOS_USGS,
    MAGNITUD_MINIMA_HISTORICO,
    MAX_REINTENTOS,
    NOMBRE_DATASET,
    ANIOS_HISTORICO,
    RUTA_PARQUET,
    RUTA_METADATA,
    TIMEOUT_SEGUNDOS,
    URL_API_USGS,
    URL_API_USGS_COUNT,
    ZONA_HORARIA_PERU,
)

RUTA_LOG = os.path.join(DIR_LOGS, "ingesta.log")


class FormateadorHoraLima(logging.Formatter):
    """
    Formatter que muestra las marcas de tiempo del log SIEMPRE en hora de Lima
    (Perú, UTC-5).
    """

    def converter(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp, tz=ZONA_HORARIA_PERU).timetuple()


_formateador_log = FormateadorHoraLima(
    fmt="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handler_archivo = logging.FileHandler(RUTA_LOG, encoding="utf-8")
_handler_archivo.setFormatter(_formateador_log)

_handler_consola = logging.StreamHandler(sys.stdout)
_handler_consola.setFormatter(_formateador_log)

logging.basicConfig(level=logging.INFO, handlers=[_handler_archivo, _handler_consola])
log = logging.getLogger("ingesta_sismos")


def peticion_con_reintentos(url: str, parametros: dict) -> requests.Response:
    """Ejecuta un GET con reintentos y backoff exponencial ante fallas de red."""
    ultimo_error = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            log.info(f"Intento {intento}/{MAX_REINTENTOS} -> GET {url}")
            respuesta = requests.get(
                url,
                params=parametros,
                headers=HEADERS_PETICION,
                timeout=TIMEOUT_SEGUNDOS,
            )
            respuesta.raise_for_status()
            log.info(f"Respuesta OK - status {respuesta.status_code}")
            return respuesta

        except requests.exceptions.Timeout:
            ultimo_error = "Timeout: la API no respondió a tiempo."
        except requests.exceptions.ConnectionError:
            ultimo_error = "Error de conexión: sin acceso a internet o DNS."
        except requests.exceptions.HTTPError as e:
            status = respuesta.status_code if "respuesta" in dir() else "N/A"
            if status == 400:
                log.error(f"Error 400 (parámetros inválidos): {e}")
                raise
            ultimo_error = f"Error HTTP {status}: {e}"
        except requests.exceptions.RequestException as e:
            ultimo_error = f"Error inesperado de red: {e}"

        espera = ESPERA_BASE_SEGUNDOS * (2 ** (intento - 1))
        log.warning(f"{ultimo_error} - reintentando en {espera}s...")
        time.sleep(espera)

    log.error(f"Se agotaron los {MAX_REINTENTOS} reintentos. Abortando.")
    raise RuntimeError(f"No se pudo completar la petición tras {MAX_REINTENTOS} intentos: {ultimo_error}")


def contar_eventos(parametros_base: dict) -> int:
    parametros = {**parametros_base, "format": "text"}
    respuesta = peticion_con_reintentos(URL_API_USGS_COUNT, parametros)
    try:
        return int(respuesta.text.strip())
    except ValueError:
        return 0


def descargar_rango(fecha_inicio: str, fecha_fin: str, parametros_base: dict) -> list:
    parametros = {
        **parametros_base,
        "format": "geojson",
        "starttime": fecha_inicio,
        "endtime": fecha_fin,
        "orderby": "time",
    }
    respuesta = peticion_con_reintentos(URL_API_USGS, parametros)
    datos = respuesta.json()
    features = datos.get("features", [])
    log.info(f"  Rango {fecha_inicio} -> {fecha_fin}: {len(features)} eventos descargados")
    return features


def ingesta_historica_peru(anios: int = ANIOS_HISTORICO, magnitud_minima: float = MAGNITUD_MINIMA_HISTORICO) -> list:
    """Descarga el histórico de sismos de Perú desde la API de la USGS."""
    fecha_fin = datetime.date.today()
    fecha_inicio_total = fecha_fin - datetime.timedelta(days=365 * anios)

    parametros_base = {**BBOX_PERU, "minmagnitude": magnitud_minima}

    log.info("=" * 70)
    log.info("INICIO DE INGESTA HISTÓRICA - Sismos en Perú (USGS)")
    log.info(f"Ventana temporal : {fecha_inicio_total.isoformat()} -> {fecha_fin.isoformat()}")
    log.info(f"Bounding box      : {BBOX_PERU}")
    log.info(f"Magnitud mínima   : {magnitud_minima}")
    log.info("=" * 70)

    total_estimado = contar_eventos({
        **parametros_base,
        "starttime": fecha_inicio_total.isoformat(),
        "endtime": fecha_fin.isoformat(),
    })
    log.info(f"Conteo total estimado de eventos: {total_estimado}")

    todas_las_features = []

    if total_estimado <= LIMITE_EVENTOS_USGS:
        todas_las_features = descargar_rango(
            fecha_inicio_total.isoformat(), fecha_fin.isoformat(), parametros_base
        )
    else:
        log.warning(
            f"El conteo ({total_estimado}) supera el límite de {LIMITE_EVENTOS_USGS} "
            "por petición. Se particionará la descarga por años."
        )
        anio_actual = fecha_inicio_total
        while anio_actual < fecha_fin:
            siguiente = min(anio_actual + datetime.timedelta(days=365), fecha_fin)
            features = descargar_rango(anio_actual.isoformat(), siguiente.isoformat(), parametros_base)
            todas_las_features.extend(features)
            anio_actual = siguiente
            time.sleep(ESPERA_ENTRE_PETICIONES)

    log.info(f"Ingesta finalizada. Total de eventos obtenidos: {len(todas_las_features)}")
    return todas_las_features


def _normalizar_lote(features: list) -> pd.DataFrame:
    """Normaliza un lote acotado de objetos GeoJSON."""
    registros = []
    for sismo in features:
        propiedades = sismo.get("properties", {})
        geometria = sismo.get("geometry", {}) or {}
        coordenadas = geometria.get("coordinates", [None, None, None])

        tiempo_ms = propiedades.get("time")
        fecha_utc = (
            datetime.datetime.fromtimestamp(tiempo_ms / 1000.0, tz=datetime.timezone.utc)
            if tiempo_ms is not None
            else None
        )

        registros.append({
            "id_usgs": sismo.get("id"),
            "fecha_hora_utc": fecha_utc,
            "magnitud": propiedades.get("mag"),
            "tipo_magnitud": propiedades.get("magType"),
            "lugar": propiedades.get("place"),
            "profundidad_km": coordenadas[2] if len(coordenadas) > 2 else None,
            "longitud": coordenadas[0],
            "latitud": coordenadas[1],
            "alerta_tsunami": propiedades.get("tsunami"),
            "significancia": propiedades.get("sig"),
            "num_estaciones": propiedades.get("nst"),
            "gap_azimutal": propiedades.get("gap"),
            "rms": propiedades.get("rms"),
            "estado_revision": propiedades.get("status"),
            "tipo_evento": propiedades.get("type"),
            "url_detalle": propiedades.get("url"),
        })

    return pd.DataFrame(registros)


def normalizar_sismos(features: list, tamano_lote: int = 5_000) -> pd.DataFrame:
    """Aplana GeoJSON por lotes para limitar el pico de memoria.

    La interfaz se mantiene compatible con el resto del proyecto, pero la
    construcción interna deja de acumular todos los diccionarios normalizados
    simultáneamente. ``tamano_lote`` permite demostrar escalabilidad.
    """
    if tamano_lote <= 0:
        raise ValueError("tamano_lote debe ser mayor que cero.")
    log.info("Normalizando %s eventos en lotes de %s...", len(features), tamano_lote)
    lotes = [
        _normalizar_lote(features[inicio : inicio + tamano_lote])
        for inicio in range(0, len(features), tamano_lote)
    ]
    df = pd.concat(lotes, ignore_index=True) if lotes else _normalizar_lote([])
    log.info(f"Normalización completa: {df.shape[0]} filas x {df.shape[1]} columnas")
    return df


def guardar_parquet(df: pd.DataFrame, ruta: str = RUTA_PARQUET) -> str:
    """Persiste Parquet comprimido con grupos de filas aptos para lectura selectiva."""
    df = df.sort_values("fecha_hora_utc").reset_index(drop=True)
    df.to_parquet(
        ruta,
        engine="pyarrow",
        compression="zstd",
        index=False,
        row_group_size=10_000,
    )
    tam_kb = os.path.getsize(ruta) / 1024
    log.info(f"Dataset Parquet guardado en: {ruta} ({tam_kb:.2f} KB)")
    guardar_metadata_sincronizacion(len(df))
    return ruta


def guardar_metadata_sincronizacion(total_eventos: int, eventos_recibidos: int | None = None) -> dict:
    """Registra cuándo terminó una consulta válida, aunque no hubiera eventos nuevos."""
    metadata = {
        "fuente": "USGS FDSN Event Web Service",
        "ultima_sincronizacion_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_eventos": int(total_eventos),
        "eventos_recibidos": None if eventos_recibidos is None else int(eventos_recibidos),
    }
    temporal = f"{RUTA_METADATA}.tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(metadata, archivo, ensure_ascii=False, indent=2)
    os.replace(temporal, RUTA_METADATA)
    return metadata


def obtener_metadata_ingesta() -> dict | None:
    """Lee evidencia de sincronización; devuelve None si aún no existe o está dañada."""
    try:
        with open(RUTA_METADATA, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def leer_sismos_parquet(
    ruta: str = RUTA_PARQUET,
    columnas: list[str] | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
) -> pd.DataFrame:
    """Lee solo columnas y rangos necesarios mediante filtros de PyArrow."""
    filtros = []
    if fecha_inicio:
        filtros.append(("fecha_hora_utc", ">=", pd.to_datetime(fecha_inicio, utc=True)))
    if fecha_fin:
        filtros.append(("fecha_hora_utc", "<", pd.to_datetime(fecha_fin, utc=True)))
    tabla = pq.read_table(ruta, columns=columnas, filters=filtros or None)
    return tabla.to_pandas()


def ejecutar_ingesta_completa(forzar: bool = False) -> str:
    """
    Punto de entrada de la capa de ingesta para la carga histórica completa.

    Si ya existe un Parquet cacheado y `forzar=False`, no vuelve a consultar la
    API.
    """
    if os.path.exists(RUTA_PARQUET) and not forzar:
        log.info(f"Se encontró caché Parquet existente en {RUTA_PARQUET}. Se omite la descarga.")
        return RUTA_PARQUET

    inicio_proceso = time.time()
    features = ingesta_historica_peru()

    if not features:
        log.warning("No se obtuvieron eventos. Finalizando sin generar dataset.")
        raise RuntimeError("La API de la USGS no devolvió eventos para la ventana solicitada.")

    df = normalizar_sismos(features)
    ruta = guardar_parquet(df)

    duracion = time.time() - inicio_proceso
    log.info(f"PROCESO DE INGESTA COMPLETADO EXITOSAMENTE en {duracion:.1f}s")
    log.info("=" * 70)
    return ruta


def actualizar_incrementalmente(margen_dias: int = 2) -> str:
    """
    Descarga SOLO los eventos nuevos (o revisados) desde la última fecha
    registrada en el Parquet cacheado hasta hoy, y los fusiona con el
    histórico existente (deduplicando por `id_usgs`).

    Es mucho más liviano que volver a descargar 50 años completos: por eso es
    lo que permite mantener el dataset al día de forma automática, sin
    sobrecargar la API de la USGS. `margen_dias` retrocede un par de días
    sobre la última fecha cacheada para capturar eventos cuya magnitud fue
    revisada después de ocurridos.
    """
    if not os.path.exists(RUTA_PARQUET):
        log.info("No existe caché Parquet todavía; se ejecuta la ingesta histórica completa.")
        return ejecutar_ingesta_completa(forzar=True)

    df_actual = leer_sismos_parquet()
    ultima_fecha_cacheada = df_actual["fecha_hora_utc"].max()

    fecha_inicio = (ultima_fecha_cacheada - datetime.timedelta(days=margen_dias)).date().isoformat()
    fecha_fin = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    log.info("=" * 70)
    log.info("ACTUALIZACIÓN INCREMENTAL - Sismos en Perú (USGS)")
    log.info(f"Último evento cacheado : {ultima_fecha_cacheada}")
    log.info(f"Buscando eventos nuevos: {fecha_inicio} -> {fecha_fin}")
    log.info("=" * 70)

    parametros_base = {**BBOX_PERU, "minmagnitude": MAGNITUD_MINIMA_HISTORICO}
    try:
        features_nuevas = descargar_rango(fecha_inicio, fecha_fin, parametros_base)
    except Exception as e:
        log.warning(f"No se pudo completar la actualización incremental ({e}). Se conserva el caché existente.")
        return RUTA_PARQUET

    if not features_nuevas:
        log.info("Sin eventos nuevos desde la última actualización. El caché ya está al día.")
        guardar_metadata_sincronizacion(len(df_actual), eventos_recibidos=0)
        return RUTA_PARQUET

    df_nuevo = normalizar_sismos(features_nuevas)
    total_antes = len(df_actual)

    df_combinado = (
        pd.concat([df_actual, df_nuevo], ignore_index=True)
        .drop_duplicates(subset="id_usgs", keep="last")
        .sort_values("fecha_hora_utc")
        .reset_index(drop=True)
    )
    guardar_parquet(df_combinado)

    log.info(f"Actualización incremental completa: {len(df_combinado) - total_antes} eventos nuevos incorporados.")
    log.info("=" * 70)
    return RUTA_PARQUET


def asegurar_datos_actualizados(horas_maximas_antiguedad: int = 24) -> str:
    """
    Punto de entrada usado por el dashboard (`app.py`) en cada carga.

    - Si el Parquet no existe: corre la ingesta histórica completa (50 años).
    - Si existe pero el último evento cacheado tiene más de
      `horas_maximas_antiguedad` horas: dispara `actualizar_incrementalmente`
      (liviana, solo trae lo nuevo) en vez de volver a descargar todo.
    - Si ya está al día: no hace ninguna petición a la API.

    Así el dataset histórico se mantiene actualizado de forma AUTOMÁTICA, sin
    que nadie tenga que ejecutar nada manualmente.
    """
    if not os.path.exists(RUTA_PARQUET):
        return ejecutar_ingesta_completa(forzar=True)

    try:
        metadata = obtener_metadata_ingesta()
        if metadata is None:
            log.info("No hay evidencia de sincronización previa; se verifica la fuente incrementalmente.")
            return actualizar_incrementalmente()
        ultima_sincronizacion = pd.to_datetime(
            metadata["ultima_sincronizacion_utc"], utc=True
        ).to_pydatetime()
        antiguedad = datetime.datetime.now(datetime.timezone.utc) - ultima_sincronizacion

        if antiguedad > datetime.timedelta(hours=horas_maximas_antiguedad):
            log.info(f"Caché sin sincronizar hace {antiguedad}. Se dispara actualización incremental.")
            return actualizar_incrementalmente()

        log.info(f"El caché Parquet está sincronizado (última consulta: {ultima_sincronizacion}).")
        return RUTA_PARQUET

    except Exception as e:
        log.warning(f"No se pudo verificar la antigüedad del caché ({e}). Se usa el Parquet existente tal cual.")
        return RUTA_PARQUET


if __name__ == "__main__":
    try:
        ejecutar_ingesta_completa(forzar=True)
    except Exception as e:
        log.error(f"El proceso de ingesta terminó con error: {e}")
        raise SystemExit(1)
