"""
Componentes reutilizables de la interfaz: sidebar de filtros, panel de alertas recientes (refrescado cada 5 minutos) y visor de logs.
"""

import datetime
import logging
import os

import pandas as pd
import requests
import streamlit as st
from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder, GridUpdateMode, JsCode

from ingesta.cliente_usgs import peticion_con_reintentos
from ingesta.configuracion import (
    BBOX_PERU,
    DIR_LOGS,
    MAGNITUD_MINIMA_HISTORICO,
    TIMEOUT_IGP_SEGUNDOS,
    URL_API_USGS,
    URL_IGP_SISMOS_REPORTADOS,
    URL_IGP_ULTIMO_SISMO,
    ZONA_HORARIA_PERU,
)
from transformacion.procesamiento import departamento_mas_cercano, departamento_y_distancia_km
from visualizacion import estilos

# Ventana de búsqueda para la tabla de "últimos sismos": 
DIAS_VENTANA_ULTIMOS_SISMOS = 180

# Ventana del panel de "alertas recientes" y magnitud mínima considerada
DIAS_VENTANA_ALERTAS = 2
MAGNITUD_MINIMA_ALERTAS = 2.5

log = logging.getLogger("dashboard")

SEGUNDOS_REFRESCO_ALERTAS = 300  # 5 minutos

# Columnas que se muestran en la tabla de últimos sismos.
COLUMNAS_TABLA_SISMOS = {
    "fecha_hora_lima": "Fecha y hora (Lima)",
    "departamento": "Departamento",
    "latitud": "Latitud",
    "longitud": "Longitud",
    "profundidad_km": "Profundidad (km)",
    "magnitud": "Magnitud",
    "lugar": "Lugar",
    "tipo_evento": "Tipo de evento",
}


def controles_sistema_sidebar() -> tuple[str, bool]:
    """
    Controles del sidebar que NO dependen del dataset (se pueden dibujar
    antes de cargar los datos): selector de tema (Claro/Oscuro) y pausa de
    la actualización automática cada 5 minutos. Se pone tema por defecto el oscurito.
    """
    st.sidebar.header("⚙️ Controles del sistema")

    tema = st.sidebar.radio(
        "🎨 Tema", ["Oscuro", "Claro"], horizontal=True, key="tema_seleccionado",
        help="Cambia los colores del dashboard. No requiere recargar la página.",
    )

    pausado = st.sidebar.checkbox(
        "⏸️ Pausar actualización automática", key="autorefresco_pausado",
        help="Si lo activas, el dashboard deja de refrescarse solo cada 5 minutos.",
    )
    if pausado:
        st.sidebar.caption("⏸️ Actualización automática pausada.")
    else:
        st.sidebar.caption(f"🔄 Se refresca automáticamente cada {SEGUNDOS_REFRESCO_ALERTAS // 60} minutos.")

    st.sidebar.divider()
    return tema, pausado


def sidebar_filtros(df: pd.DataFrame) -> dict:
    """Dibuja los controles del sidebar y devuelve los valores elegidos."""
    st.sidebar.header("🔎 Filtros del dashboard")

    fecha_min = df["fecha_hora_lima"].min().date()
    fecha_max_datos = df["fecha_hora_lima"].max().date()
    fecha_hoy = datetime.datetime.now(ZONA_HORARIA_PERU).date()

    rango_fechas = st.sidebar.date_input(
        "Rango de fechas (hora de Lima)",
        value=(fecha_min, fecha_hoy),
        min_value=fecha_min,
        max_value=fecha_hoy,
        help="Filtra los sismos según su fecha de ocurrencia, en hora local de Lima (UTC-5).",
    )
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas
    else:
        fecha_inicio, fecha_fin = fecha_min, fecha_hoy

    rango_magnitud = st.sidebar.slider(
        "Magnitud",
        min_value=float(df["magnitud"].min()),
        max_value=float(df["magnitud"].max()),
        value=(float(df["magnitud"].min()), float(df["magnitud"].max())),
        step=0.1,
        help="Filtra los sismos según su magnitud registrada.",
    )

    rango_profundidad = st.sidebar.slider(
        "Profundidad (km)",
        min_value=float(df["profundidad_km"].min()),
        max_value=float(df["profundidad_km"].max()),
        value=(float(df["profundidad_km"].min()), float(df["profundidad_km"].max())),
        step=5.0,
        help="Filtra los sismos según la profundidad del hipocentro.",
    )

    departamentos_disponibles = sorted(df["departamento"].dropna().unique().tolist())
    departamentos_elegidos = st.sidebar.multiselect(
        "Departamento",
        options=departamentos_disponibles,
        default=[],
        help="Deja vacío para incluir todos los departamentos.",
    )

    st.sidebar.divider()
    st.sidebar.caption(
        f"Dataset histórico: {len(df):,} sismos registrados "
        f"({fecha_min.strftime('%Y')} - {fecha_max_datos.strftime('%Y')})."
    )

    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "magnitud_min": rango_magnitud[0],
        "magnitud_max": rango_magnitud[1],
        "profundidad_min": rango_profundidad[0],
        "profundidad_max": rango_profundidad[1],
        "departamentos": departamentos_elegidos,
    }


def aviso_datos_actualizados(df: pd.DataFrame) -> None:
    """
    Aviso con la fecha y hora de la última verificación del sistema. Se recalcula cada vez que se
    renderiza la página, así que siempre refleja el momento en que la app revisó los datos.
    """
    ahora_lima = datetime.datetime.now(ZONA_HORARIA_PERU)
    st.metric("🔄 Última verificación", ahora_lima.strftime("%d/%m/%Y %H:%M"))


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """Aplica al DataFrame los valores devueltos por `sidebar_filtros`."""
    resultado = df[
        (df["fecha_hora_lima"].dt.date >= filtros["fecha_inicio"])
        & (df["fecha_hora_lima"].dt.date <= filtros["fecha_fin"])
        & (df["magnitud"].between(filtros["magnitud_min"], filtros["magnitud_max"]))
        & (df["profundidad_km"].between(filtros["profundidad_min"], filtros["profundidad_max"]))
    ]
    if filtros["departamentos"]:
        resultado = resultado[resultado["departamento"].isin(filtros["departamentos"])]
    return resultado


@st.cache_data(ttl=SEGUNDOS_REFRESCO_ALERTAS, show_spinner="Consultando los últimos sismos en Perú (USGS)...")
def obtener_ultimos_sismos_peru(cantidad: int = 30) -> pd.DataFrame:
    """Consulta los eventos USGS más recientes dentro del bbox configurado.

    La respuesta se conserva en caché durante cinco minutos.
    """
    fecha_inicio = (
        datetime.date.today() - datetime.timedelta(days=DIAS_VENTANA_ULTIMOS_SISMOS)
    ).isoformat()
    fecha_fin = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    parametros = {
        **BBOX_PERU,
        "minmagnitude": MAGNITUD_MINIMA_HISTORICO,
        "starttime": fecha_inicio,
        "endtime": fecha_fin,
        "orderby": "time",  # más reciente primero
        "format": "geojson",
    }

    try:
        respuesta = peticion_con_reintentos(URL_API_USGS, parametros)
        datos = respuesta.json()
    except Exception as e:
        log.error(f"No se pudo obtener el listado de últimos sismos: {e}")
        st.warning("⚠️ No se pudo consultar el feed en vivo de la USGS en este momento.")
        return pd.DataFrame()

    registros = []
    for evento in datos.get("features", []):
        propiedades = evento.get("properties", {})
        geometria = evento.get("geometry", {}) or {}
        coordenadas = geometria.get("coordinates", [None, None, None])
        lon, lat = coordenadas[0], coordenadas[1]

        if lon is None or lat is None:
            continue

        tiempo_ms = propiedades.get("time")
        fecha_utc = (
            datetime.datetime.fromtimestamp(tiempo_ms / 1000.0, tz=datetime.timezone.utc)
            if tiempo_ms is not None else None
        )
        registros.append({
            "fecha_hora_utc": fecha_utc,
            "latitud": lat,
            "longitud": lon,
            "profundidad_km": coordenadas[2] if len(coordenadas) > 2 else None,
            "magnitud": propiedades.get("mag"),
            "tipo_magnitud": propiedades.get("magType"),
            "lugar": propiedades.get("place"),
            "tipo_evento": propiedades.get("type"),
            "estado_revision": propiedades.get("status"),
        })

    df = pd.DataFrame(registros)
    if df.empty:
        return df

    df = df[df["magnitud"] > MAGNITUD_MINIMA_HISTORICO].copy()
    if df.empty:
        return df

    df["fecha_hora_lima"] = df["fecha_hora_utc"].dt.tz_convert(ZONA_HORARIA_PERU)
    df["departamento"] = df.apply(
        lambda fila: departamento_mas_cercano(fila["latitud"], fila["longitud"]), axis=1
    )
    df = df.sort_values("fecha_hora_utc", ascending=False).head(cantidad).reset_index(drop=True)
    log.info(
        f"Últimos sismos en Perú: {len(df)} eventos M>{MAGNITUD_MINIMA_HISTORICO} "
        f"(ventana de {DIAS_VENTANA_ULTIMOS_SISMOS} días)."
    )
    return df


@st.cache_data(ttl=SEGUNDOS_REFRESCO_ALERTAS, show_spinner="Consultando los últimos sismos en Perú (IGP)...")
def obtener_ultimos_sismos_igp(cantidad: int = 30) -> pd.DataFrame:
    """
    Consulta en vivo la capa WFS del IGP (`sismos_reportados`, "año en curso"),
    pidiendo directamente los `cantidad` eventos más recientes ya ordenados
    por fecha/hora descendente (`sortBy`, `count`). 

    El IGP no es una API oficial/documentada, así que esta función usa
    `peticion_con_reintentos` (igual que las llamadas a la USGS) para darle
    resiliencia ante fallos pasajeros.
    """
    parametros = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "sismos_reportados:peru_igp_008_sismos_reportados",
        "outputFormat": "application/json",
        "count": cantidad,
        "sortBy": "fecha D,hora D",
    }

    try:
        respuesta = peticion_con_reintentos(URL_IGP_SISMOS_REPORTADOS, parametros)
        datos = respuesta.json()
        caracteristicas = datos.get("features") or []
        if not caracteristicas:
            raise ValueError("El IGP respondió sin eventos (features vacío).")

        registros = []
        for evento in caracteristicas:
            propiedades = evento.get("properties", {}) or {}
            fecha_raw = propiedades.get("fecha")
            hora_raw = propiedades.get("hora")
            lat = propiedades.get("lat")
            lon = propiedades.get("lon")
            if not fecha_raw or not hora_raw or lat is None or lon is None:
                continue

            # `fecha` viene como ISO ("2026-08-14T05:00:00Z"): 
            fecha_parte = fecha_raw.split("T")[0]
            fecha_hora_naive = datetime.datetime.strptime(
                f"{fecha_parte} {hora_raw}", "%Y-%m-%d %H:%M:%S"
            )
            fecha_hora_lima = fecha_hora_naive.replace(tzinfo=ZONA_HORARIA_PERU)
            fecha_hora_utc = fecha_hora_lima.astimezone(datetime.timezone.utc)

            departamento, distancia_km = departamento_y_distancia_km(lat, lon)
            lugar = (
                f"~{distancia_km:.0f} km de {departamento}"
                if distancia_km is not None else "Sin referencia"
            )

            registros.append({
                "fecha_hora_utc": fecha_hora_utc,
                "fecha_hora_lima": fecha_hora_lima,
                "latitud": lat,
                "longitud": lon,
                "profundidad_km": propiedades.get("prof"),
                "magnitud": propiedades.get("magnitud"),
                "lugar": lugar,
                "tipo_evento": "Sismo",
                "departamento": departamento,
            })

        df = pd.DataFrame(registros)
        if df.empty:
            raise ValueError("El IGP respondió pero ningún evento tenía datos utilizables.")

        df = df.sort_values("fecha_hora_utc", ascending=False).head(cantidad).reset_index(drop=True)
        log.info(f"Últimos sismos en Perú (IGP): {len(df)} eventos.")
        return df

    except Exception as e:
        log.warning(f"IGP no disponible para la tabla de últimos sismos, usando USGS como respaldo: {e}")
        return obtener_ultimos_sismos_peru(cantidad)


def tabla_ultimos_sismos(cantidad: int = 30) -> None:
    """Muestra los eventos recientes del IGP, con USGS como fuente de respaldo."""
    st.markdown(f"##### 📋 Últimos {cantidad} sismos reportados en Perú")
    st.caption(
        "Fuente: IGP (Instituto Geofísico del Perú), con respaldo automático a la USGS "
        "si el IGP no responde. Ordenados del más reciente al más antiguo. "
        "Se actualiza automáticamente cada 5 minutos; no requiere ninguna acción manual."
    )

    df_ultimos = obtener_ultimos_sismos_igp(cantidad)

    if df_ultimos.empty:
        st.info("No se pudieron obtener sismos recientes de ninguna de las dos fuentes en este momento.")
        return

    columnas_disponibles = [c for c in COLUMNAS_TABLA_SISMOS if c in df_ultimos.columns]
    tabla = df_ultimos[columnas_disponibles].rename(columns=COLUMNAS_TABLA_SISMOS).copy()
    tabla["Fecha y hora (Lima)"] = tabla["Fecha y hora (Lima)"].dt.strftime("%d/%m/%Y %H:%M")

    constructor_grilla = GridOptionsBuilder.from_dataframe(tabla)
    constructor_grilla.configure_default_column(resizable=True, sortable=True, filter=True)
    constructor_grilla.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=cantidad)
    constructor_grilla.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
    constructor_grilla.configure_column("Fecha y hora (Lima)", sort="desc")

    # Colorea la columna de magnitud según severidad.
    estilo_celda_magnitud = JsCode(
        """
        function(params) {
            if (params.value >= 7) {
                return {'color': 'white', 'backgroundColor': 'firebrick'};
            } else if (params.value >= 6) {
                return {'color': 'white', 'backgroundColor': 'chocolate'};
            } else if (params.value >= 5) {
                return {'color': 'white', 'backgroundColor': 'olivedrab'};
            }
            return {'color': 'white'};
        };
        """
    )
    constructor_grilla.configure_column("Magnitud", cellStyle=estilo_celda_magnitud)

    opciones_grilla = constructor_grilla.build()

    AgGrid(
        tabla,
        gridOptions=opciones_grilla,
        height=480,
        theme="streamlit",
        update_mode=GridUpdateMode.NO_UPDATE,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        allow_unsafe_jscode=True,
    )

    st.download_button(
        label="⬇️ Descargar tabla como CSV",
        data=tabla.to_csv(index=False).encode("utf-8"),
        file_name="ultimos_sismos_peru.csv",
        mime="text/csv",
    )


@st.cache_data(ttl=SEGUNDOS_REFRESCO_ALERTAS, show_spinner="Consultando sismos recientes (USGS)...")
def obtener_sismos_recientes() -> pd.DataFrame:
    """
    Consulta en vivo la API de la USGS (bbox de Perú, magnitud >= 2.5,
    últimas `DIAS_VENTANA_ALERTAS` días) directamente contra el endpoint de
    consulta en tiempo real — no contra un feed resumen pre-generado.
    """
    fecha_inicio = (datetime.date.today() - datetime.timedelta(days=DIAS_VENTANA_ALERTAS)).isoformat()
    fecha_fin = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    parametros = {
        **BBOX_PERU,
        "minmagnitude": MAGNITUD_MINIMA_ALERTAS,
        "starttime": fecha_inicio,
        "endtime": fecha_fin,
        "orderby": "time",
        "format": "geojson",
    }

    try:
        respuesta = peticion_con_reintentos(URL_API_USGS, parametros)
        datos = respuesta.json()
    except Exception as e:
        log.error(f"No se pudo obtener el listado de alertas recientes: {e}")
        st.warning("⚠️ No se pudo consultar el feed de alertas recientes de la USGS en este momento.")
        return pd.DataFrame()

    registros = []
    for evento in datos.get("features", []):
        propiedades = evento.get("properties", {})
        geometria = evento.get("geometry", {}) or {}
        coordenadas = geometria.get("coordinates", [None, None, None])
        lon, lat = coordenadas[0], coordenadas[1]

        if lon is None or lat is None:
            continue

        tiempo_ms = propiedades.get("time")
        fecha_utc = (
            datetime.datetime.fromtimestamp(tiempo_ms / 1000.0, tz=datetime.timezone.utc)
            if tiempo_ms is not None else None
        )
        registros.append({
            "fecha_hora_utc": fecha_utc,
            "lugar": propiedades.get("place"),
            "magnitud": propiedades.get("mag"),
            "profundidad_km": coordenadas[2] if len(coordenadas) > 2 else None,
            "alerta_tsunami": propiedades.get("tsunami"),
            "url_detalle": propiedades.get("url"),
        })

    df = pd.DataFrame(registros)
    if not df.empty:
        df["fecha_hora_lima"] = df["fecha_hora_utc"].dt.tz_convert(ZONA_HORARIA_PERU)
        df = df.sort_values("fecha_hora_utc", ascending=False)
    log.info(f"Panel de alertas: {len(df)} eventos recientes en el área de Perú (consulta en vivo).")
    return df


@st.cache_data(ttl=SEGUNDOS_REFRESCO_ALERTAS, show_spinner=False)
def obtener_ultimo_sismo_igp() -> dict | None:
    """
    Consulta el endpoint WFS/GeoServer del IGP (Instituto Geofísico del Perú)
    que devuelve el último sismo detectado por la red sísmica nacional.
    """
    try:
        respuesta = requests.get(URL_IGP_ULTIMO_SISMO, timeout=TIMEOUT_IGP_SEGUNDOS)
        respuesta.raise_for_status()
        datos = respuesta.json()

        caracteristicas = datos.get("features") or []
        if not caracteristicas:
            log.info("IGP: el endpoint respondió pero sin eventos (features vacío).")
            return None

        propiedades = caracteristicas[0].get("properties") or {}
        if not propiedades.get("fecha_local") or propiedades.get("magnitud") is None:
            log.info("IGP: respuesta con estructura inesperada, se omite el widget.")
            return None

        return propiedades
    except Exception as e:
        log.info(f"IGP: endpoint no disponible en este momento, se omite el widget ({e}).")
        return None


def widget_ultimo_sismo_igp() -> None:
    """
    Widget complementario con el último sismo reportado por el IGP.
    """
    ultimo = obtener_ultimo_sismo_igp()
    if ultimo is None:
        return

    st.markdown("##### 🇵🇪 Último sismo reportado por el IGP")
    st.caption(
        "Fuente complementaria: Instituto Geofísico del Perú (no oficial/documentada). "
        "Puede detectar eventos locales que la USGS aún no publicó."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Magnitud", ultimo.get("magnitud", "—"))
    col2.metric("Profundidad (km)", ultimo.get("profundidad", "—"))
    fecha_local = ultimo.get("fecha_local", "")
    hora_local = ultimo.get("hora_local", "")
    col3.metric("Fecha y hora (Lima)", f"{fecha_local} {hora_local}".strip())

    referencia = ultimo.get("referencia")
    if referencia:
        st.caption(f"📍 {referencia}")


def _color_severidad_alerta(magnitud: float) -> str:
    """Color según severidad."""
    if magnitud >= 7:
        return "#B22222" 
    if magnitud >= 6:
        return "#D2691E"
    if magnitud >= 5:
        return "#6B8E23"
    return "#3498DB"  # azul (por defecto)


def panel_alertas_recientes() -> None:
    """Panel de alertas e incidentes recientes."""
    st.subheader("🚨 Alertas y panel de incidentes recientes")
    st.caption("Se refresca automáticamente cada 5 minutos.")

    widget_ultimo_sismo_igp()

    df_recientes = obtener_sismos_recientes()

    if df_recientes.empty:
        return

    con_alerta_tsunami = int((df_recientes["alerta_tsunami"] == 1).sum())
    estilos.fila_tarjetas([
        {"icono": "🚨", "titulo": "Sismos últimas 48h", "valor": str(len(df_recientes)), "color": "#F2545B"},
        {"icono": "🌋", "titulo": "Magnitud máxima", "valor": f"{df_recientes['magnitud'].max():.1f}", "color": "#F5A623"},
        {"icono": "🌊", "titulo": "Alertas de tsunami activas", "valor": str(con_alerta_tsunami), "color": "#3B82F6"},
    ])

    st.markdown("<div style='max-height: 480px; overflow-y: auto; padding-right: 6px;'>", unsafe_allow_html=True)
    for _, fila in df_recientes.iterrows():
        color = _color_severidad_alerta(fila["magnitud"])
        aviso_tsunami = (
            " &nbsp;·&nbsp; <span style='color:#E74C3C; font-weight:700;'>🌊 Alerta de tsunami</span>"
            if fila.get("alerta_tsunami") == 1 else ""
        )
        fecha_txt = fila["fecha_hora_lima"].strftime("%d/%m/%Y %H:%M") if pd.notna(fila["fecha_hora_lima"]) else "—"
        profundidad_txt = f"{fila['profundidad_km']:.0f}" if pd.notna(fila["profundidad_km"]) else "—"
        st.markdown(
            f"""
            <div style="border-left: 6px solid {color}; background-color: rgba(255,255,255,0.04);
                        border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap: 12px;">
                    <span style="font-size: 1.3rem; font-weight: 700; line-height: 1.3;">
                        📍 {fila['lugar']}
                    </span>
                    <span style="background:{color}; color:white; padding:5px 14px; border-radius:14px;
                                 font-weight:700; font-size: 1rem; white-space:nowrap;">
                        M {fila['magnitud']:.1f}
                    </span>
                </div>
                <div style="color:#AAAAAA; margin-top:6px; font-size: 0.92rem;">
                    🕒 {fecha_txt} (Lima) &nbsp;·&nbsp; ⬇️ {profundidad_txt} km{aviso_tsunami}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def mostrar_logs() -> None:
    """Muestra en un expander las últimas líneas del log de ingesta."""
    with st.expander("🪵 Ver logs del sistema (ingesta y dashboard)"):
        ruta_log = os.path.join(DIR_LOGS, "ingesta.log")
        if not os.path.exists(ruta_log):
            st.caption("Aún no se generaron logs de ingesta.")
            return
        with open(ruta_log, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        ultimas = "".join(lineas[-200:])
        st.code(ultimas or "Sin contenido registrado todavía.", language="log")
