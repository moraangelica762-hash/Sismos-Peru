"""Gráficos del análisis textual y no supervisado."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from visualizacion.graficos import _aplicar_tema_grafico


def grafico_clusters(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df,
        x="profundidad_km",
        y="magnitud",
        color="cluster",
        symbol="es_anomalia",
        hover_data=["lugar", "latitud", "longitud", "fecha_hora_lima"],
        opacity=0.7,
        title="Patrones históricos: clusters y eventos atípicos",
        labels={
            "profundidad_km": "Profundidad (km)",
            "magnitud": "Magnitud",
            "cluster": "Cluster",
            "es_anomalia": "Atípico",
        },
    )
    fig.update_layout(height=500)
    return _aplicar_tema_grafico(fig)


def grafico_contexto_textual(df: pd.DataFrame) -> go.Figure:
    conteo = df["contexto_textual"].value_counts().rename_axis("contexto").reset_index(name="eventos")
    fig = px.bar(
        conteo,
        x="contexto",
        y="eventos",
        color="eventos",
        color_continuous_scale="Blues",
        title="Cobertura del texto descriptivo de USGS",
        labels={"contexto": "Tipo de descripción", "eventos": "Eventos"},
    )
    fig.update_layout(height=400, coloraxis_showscale=False)
    return _aplicar_tema_grafico(fig)
