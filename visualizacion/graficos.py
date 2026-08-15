"""
Gráficos que responden a las 5 preguntas de negocio del proyecto.

"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from visualizacion import estilos

COLOR_PRINCIPAL = "#C0392B"
ESCALA_MAGNITUD = "OrRd"


def _aplicar_tema_grafico(fig: go.Figure) -> go.Figure:
    c = estilos.colores_grafico()
    fig.update_layout(
        plot_bgcolor=c["plot_bgcolor"],
        paper_bgcolor=c["paper_bgcolor"],
        font_color=c["font_color"],
        legend_font_color=c["font_color"],
    )
    fig.update_xaxes(gridcolor=c["gridcolor"], zerolinecolor=c["gridcolor"])
    fig.update_yaxes(gridcolor=c["gridcolor"], zerolinecolor=c["gridcolor"])
    return fig


def grafico_evolucion_frecuencia(df: pd.DataFrame) -> go.Figure:
    """P1: ¿Cómo ha evolucionado la frecuencia de los terremotos en los últimos 50 años?"""
    conteo_anual = df.groupby("anio").size().reset_index(name="cantidad_sismos")
    fig = px.line(
        conteo_anual,
        x="anio",
        y="cantidad_sismos",
        markers=True,
        title="Evolución anual de la frecuencia de sismos en Perú",
        labels={"anio": "Año", "cantidad_sismos": "Cantidad de sismos"},
    )
    fig.update_traces(line_color=COLOR_PRINCIPAL)
    fig.update_layout(height=420)
    return _aplicar_tema_grafico(fig)


def grafico_regiones_actividad(df: pd.DataFrame, top_n: int = 12) -> go.Figure:
    """P2: ¿Qué regiones (departamentos) presentan mayor actividad sísmica?"""
    conteo_region = (
        df["departamento"].value_counts().head(top_n).reset_index()
    )
    conteo_region.columns = ["departamento", "cantidad_sismos"]
    fig = px.bar(
        conteo_region.sort_values("cantidad_sismos"),
        x="cantidad_sismos",
        y="departamento",
        orientation="h",
        color="cantidad_sismos",
        color_continuous_scale=ESCALA_MAGNITUD,
        title=f"Top {top_n} departamentos con mayor actividad sísmica",
        labels={"cantidad_sismos": "Cantidad de sismos", "departamento": "Departamento"},
    )
    fig.update_layout(height=450, coloraxis_showscale=False)
    return _aplicar_tema_grafico(fig)


def grafico_distribucion_magnitudes(df: pd.DataFrame) -> go.Figure:
    """P3: ¿Cuál es la distribución de las magnitudes registradas?"""
    fig = px.histogram(
        df,
        x="magnitud",
        nbins=30,
        title="Distribución de magnitudes registradas",
        labels={"magnitud": "Magnitud", "count": "Frecuencia"},
        color_discrete_sequence=[COLOR_PRINCIPAL],
    )
    fig.add_vline(
        x=df["magnitud"].mean(), line_dash="dash", line_color="gray",
        annotation_text=f"Media = {df['magnitud'].mean():.2f}",
    )
    fig.update_layout(height=420, bargap=0.05, yaxis_title="Cantidad de sismos")
    return _aplicar_tema_grafico(fig)


def grafico_estacionalidad(df: pd.DataFrame) -> go.Figure:
    """P4: ¿Existen períodos del año con mayor ocurrencia de sismos?"""
    orden_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    conteo_mes = df.groupby("nombre_mes").size().reindex(orden_meses).reset_index(name="cantidad_sismos")
    conteo_mes.columns = ["mes", "cantidad_sismos"]
    fig = px.bar(
        conteo_mes,
        x="mes",
        y="cantidad_sismos",
        title="Cantidad de sismos por mes del año (estacionalidad)",
        labels={"mes": "Mes", "cantidad_sismos": "Cantidad de sismos"},
        color="cantidad_sismos",
        color_continuous_scale=ESCALA_MAGNITUD,
    )
    fig.update_layout(height=420, coloraxis_showscale=False)
    return _aplicar_tema_grafico(fig)


def grafico_profundidad_magnitud(df: pd.DataFrame) -> go.Figure:
    """P5: ¿Qué relación existe entre la profundidad y la magnitud de los terremotos?"""
    fig = px.scatter(
        df,
        x="profundidad_km",
        y="magnitud",
        color="categoria_profundidad",
        opacity=0.6,
        title="Relación entre profundidad y magnitud",
        labels={"profundidad_km": "Profundidad (km)", "magnitud": "Magnitud", "categoria_profundidad": "Categoría"},
        hover_data={"departamento": True, "anio": True},
    )
    fig.update_layout(height=450)
    return _aplicar_tema_grafico(fig)


def grafico_tendencia_por_region(df: pd.DataFrame, top_n: int = 6) -> go.Figure:
    """Tendencias temporales: series de frecuencia por región a lo largo de los años."""
    top_departamentos = df["departamento"].value_counts().head(top_n).index
    df_top = df[df["departamento"].isin(top_departamentos)]
    serie = df_top.groupby(["anio", "departamento"]).size().reset_index(name="cantidad_sismos")
    fig = px.line(
        serie,
        x="anio",
        y="cantidad_sismos",
        color="departamento",
        markers=True,
        title=f"Tendencia anual de sismos - Top {top_n} departamentos",
        labels={"anio": "Año", "cantidad_sismos": "Cantidad de sismos", "departamento": "Departamento"},
    )
    fig.update_layout(height=450)
    return _aplicar_tema_grafico(fig)


def grafico_histograma_profundidad(df: pd.DataFrame) -> go.Figure:
    """Histograma de profundidades, complementario al de magnitudes."""
    fig = px.histogram(
        df,
        x="profundidad_km",
        nbins=30,
        title="Distribución de profundidades",
        labels={"profundidad_km": "Profundidad (km)", "count": "Frecuencia"},
        color_discrete_sequence=["#2C3E50"],
    )
    fig.update_layout(height=420, bargap=0.05, yaxis_title="Cantidad de sismos")
    return _aplicar_tema_grafico(fig)
