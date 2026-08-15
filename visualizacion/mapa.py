"""
Mapa dinámico de epicentros con filtros de tiempo, magnitud y profundidad.

Se usa Plotly (scatter_mapbox con estilo "open-street-map", sin requerir
token) para mantener una sola librería de gráficos en todo el dashboard.
Los epicentros se colorean por categoría de severidad (en vez de una escala
continua), con un hover enriquecido tipo "tarjeta" (lugar, magnitud,
profundidad y coordenadas), buscando un estilo visual más parecido a mapas
de sismos tipo pines (Latest Earthquakes / USGS), manteniendo Plotly como
única librería de gráficos del proyecto.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Categorías de severidad y su color, en el orden en que deben aparecer en
# la leyenda (de menor a mayor magnitud).
COLOR_SEVERIDAD = {
    "Leve (M < 4)": "#2ECC71",        # verde
    "Moderado (M 4 - 5.9)": "#3498DB",  # azul
    "Fuerte (M 6 - 6.9)": "#E67E22",  # naranja
    "Mayor (M ≥ 7)": "#C0392B",       # rojo
}
ORDEN_SEVERIDAD = list(COLOR_SEVERIDAD.keys())


def _categoria_severidad(magnitud: float) -> str:
    if magnitud >= 7:
        return "Mayor (M ≥ 7)"
    if magnitud >= 6:
        return "Fuerte (M 6 - 6.9)"
    if magnitud >= 4:
        return "Moderado (M 4 - 5.9)"
    return "Leve (M < 4)"


def mapa_dinamico_sismos(df: pd.DataFrame) -> go.Figure:
    """Genera el mapa de epicentros ya filtrado por el llamador (sidebar)."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            annotations=[{
                "text": "No hay sismos que coincidan con los filtros seleccionados.",
                "showarrow": False, "font": {"size": 16},
            }],
            height=550,
        )
        return fig

    df = df.copy()
    df["categoria_severidad"] = df["magnitud"].apply(_categoria_severidad)

    fig = px.scatter_mapbox(
        df,
        lat="latitud",
        lon="longitud",
        color="categoria_severidad",
        category_orders={"categoria_severidad": ORDEN_SEVERIDAD},
        color_discrete_map=COLOR_SEVERIDAD,
        size="magnitud",
        size_max=20,
        opacity=0.85,
        hover_name="lugar",
        custom_data=["magnitud", "profundidad_km", "departamento", "fecha_hora_lima"],
        zoom=4.3,
        center={"lat": -9.19, "lon": -75.02},
        mapbox_style="open-street-map",
        title="Mapa dinámico de epicentros de sismos en Perú",
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Magnitud: <b>%{customdata[0]:.1f}</b><br>"
            "Profundidad: %{customdata[1]:.0f} km<br>"
            "Departamento: %{customdata[2]}<br>"
            "Fecha (Lima): %{customdata[3]|%d/%m/%Y %H:%M}<br>"
            "Lat/Lon: %{lat:.3f} / %{lon:.3f}"
            "<extra></extra>"
        )
    )
    fig.update_layout(
        height=560,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        legend=dict(
            title="Severidad",
            orientation="h",
            yanchor="bottom", y=0.01,
            xanchor="left", x=0.01,
            bgcolor="rgba(0,0,0,0.55)",
            font=dict(color="white"),
        ),
    )
    return fig
