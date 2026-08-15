"""
app.py — Punto de entrada de la Data App de Streamlit.

Dashboard interactivo de análisis histórico y monitoreo de sismos en Perú
(fuente: API de la USGS). Integra las tres capas del proyecto:

    ingesta/         -> descarga y cachea los datos en Parquet
    transformacion/  -> valida (Pandera) y enriquece (feature engineering)
    visualizacion/   -> gráficos, mapa y componentes de la interfaz

Ejecutar localmente con:  streamlit run app.py
"""

import logging

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from ingesta.cliente_usgs import asegurar_datos_actualizados, RUTA_PARQUET
from transformacion.esquemas import validar_sismos_crudos, validar_sismos_enriquecidos
from transformacion.procesamiento import transformar_sismos
from visualizacion import componentes, estilos, graficos, mapa

log = logging.getLogger("dashboard")

SEGUNDOS_REFRESCO_DASHBOARD = 300  # 5 minutos


# ── Configuración de página ────────────────────────────────────────────────
def configurar_pagina() -> None:
    st.set_page_config(
        page_title="Sismos en Perú | Análisis Histórico y Alertas",
        page_icon="🌋",
        layout="wide",
        initial_sidebar_state="expanded",
    )


# ── Carga de datos (cacheada) ───────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Verificando y cargando dataset histórico de sismos...")
def cargar_datos_crudos() -> pd.DataFrame:
    """
    Carga desde Parquet. Si no existe, corre la ingesta histórica completa; si
    existe pero está desactualizado (> 24h desde el último evento cacheado),
    dispara una actualización incremental automática antes de leerlo.
    """
    asegurar_datos_actualizados(horas_maximas_antiguedad=24)
    df = pd.read_parquet(RUTA_PARQUET)
    df = validar_sismos_crudos(df)
    return df


@st.cache_data(ttl=3600, show_spinner="Preparando datos para el dashboard...")
def preparar_datos(df: pd.DataFrame) -> pd.DataFrame:
    df = transformar_sismos(df)
    df = validar_sismos_enriquecidos(df)
    return df


# ── Secciones del dashboard ─────────────────────────────────────────────────
def seccion_resumen(df: pd.DataFrame) -> None:
    anios_cubiertos = df["anio"].max() - df["anio"].min()
    estilos.fila_tarjetas([
        {"icono": "📊", "titulo": "Sismos analizados", "valor": f"{len(df):,}"},
        {"icono": "🌋", "titulo": "Magnitud máxima", "valor": f"{df['magnitud'].max():.1f}"},
        {"icono": "📍", "titulo": "Departamento más activo", "valor": df["departamento"].value_counts().idxmax()},
        {"icono": "📅", "titulo": "Años de historia", "valor": f"{anios_cubiertos}"},
    ])


def seccion_mapa(df: pd.DataFrame) -> None:
    st.plotly_chart(mapa.mapa_dinamico_sismos(df), use_container_width=True, key="grafico_mapa_dinamico")
    st.divider()
    componentes.tabla_ultimos_sismos()


def seccion_tendencias(df: pd.DataFrame) -> None:
    st.plotly_chart(graficos.grafico_evolucion_frecuencia(df), use_container_width=True, key="grafico_tendencia_evolucion")
    st.plotly_chart(graficos.grafico_tendencia_por_region(df), use_container_width=True, key="grafico_tendencia_region")


def seccion_distribuciones(df: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(graficos.grafico_distribucion_magnitudes(df), use_container_width=True, key="grafico_dist_magnitudes")
    with col2:
        st.plotly_chart(graficos.grafico_histograma_profundidad(df), use_container_width=True, key="grafico_dist_profundidad")


def seccion_preguntas_de_negocio(df: pd.DataFrame) -> None:
    preguntas = [
        ("1. ¿Cómo ha evolucionado la frecuencia de los terremotos en los últimos 50 años?",
         graficos.grafico_evolucion_frecuencia, "pregunta_1"),
        ("2. ¿Qué regiones presentan mayor actividad sísmica?",
         graficos.grafico_regiones_actividad, "pregunta_2"),
        ("3. ¿Cuál es la distribución de las magnitudes registradas?",
         graficos.grafico_distribucion_magnitudes, "pregunta_3"),
        ("4. ¿Existen períodos del año con mayor ocurrencia de sismos?",
         graficos.grafico_estacionalidad, "pregunta_4"),
        ("5. ¿Qué relación existe entre la profundidad y la magnitud de los terremotos?",
         graficos.grafico_profundidad_magnitud, "pregunta_5"),
    ]
    for pregunta, funcion_grafico, clave in preguntas:
        st.markdown(f"#### {pregunta}")
        st.plotly_chart(funcion_grafico(df), use_container_width=True, key=f"grafico_{clave}")
        st.divider()


# ── Aplicación principal ─────────────────────────────────────────────────────
def main() -> None:
    configurar_pagina()

    # Controles del sistema (tema y pausa de auto-refresco): se dibujan antes
    # de cargar los datos porque no dependen de ellos, y así quedan arriba
    # del todo en el sidebar.
    tema, pausado = componentes.controles_sistema_sidebar()
    estilos.inyectar_css_global(tema)

    # Refresca automáticamente el dashboard cada 5 minutos (alertas e
    # incidentes), salvo que el usuario lo haya pausado desde el sidebar.
    if not pausado:
        st_autorefresh(interval=SEGUNDOS_REFRESCO_DASHBOARD * 1000, key="autorefresco_dashboard")

    datos_crudos = cargar_datos_crudos()
    datos = preparar_datos(datos_crudos)

    col_titulo, col_aviso = st.columns([3, 1])
    with col_titulo:
        st.title("🌋 Análisis Histórico y Alertas de Sismos en Perú")
        st.caption(
            "Data App construida con Streamlit sobre datos de la API de la USGS. "
            "Ingesta cacheada en Parquet, validación con Pandera y visualización con Plotly."
        )
    with col_aviso:
        componentes.aviso_datos_actualizados(datos)

    filtros = componentes.sidebar_filtros(datos)
    datos_filtrados = componentes.aplicar_filtros(datos, filtros)

    if datos_filtrados.empty:
        st.warning("No hay sismos que coincidan con los filtros seleccionados. Ajusta los criterios en el sidebar.")
        return

    seccion_resumen(datos_filtrados)
    st.divider()

    tab_mapa, tab_tendencias, tab_distribuciones, tab_preguntas, tab_alertas = st.tabs([
        "🗺️ Mapa dinámico",
        "📈 Tendencias temporales",
        "📊 Distribuciones",
        "❓ Preguntas de negocio",
        "🚨 Alertas recientes",
    ])

    with tab_mapa:
        seccion_mapa(datos_filtrados)
    with tab_tendencias:
        seccion_tendencias(datos_filtrados)
    with tab_distribuciones:
        seccion_distribuciones(datos_filtrados)
    with tab_preguntas:
        seccion_preguntas_de_negocio(datos_filtrados)
    with tab_alertas:
        componentes.panel_alertas_recientes()

    st.divider()
    componentes.mostrar_logs()


if __name__ == "__main__":
    main()
