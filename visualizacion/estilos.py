"""
Estilo visual del dashboard: tema claro/oscuro.
"""

import streamlit as st

PALETA_CLARO = {
    "fondo": "#F5F6FA",
    "tarjeta": "#FFFFFF",
    "texto": "#1F2430",
    "texto_tenue": "#6B7280",
    "borde": "#E5E7EB",
    "acento": "#4F46E5",
    "sombra": "rgba(15, 23, 42, 0.08)",
}

PALETA_OSCURO = {
    "fondo": "#0F1115",
    "tarjeta": "#181B22",
    "texto": "#F5F6FA",
    "texto_tenue": "#9CA3AF",
    "borde": "#2A2E38",
    "acento": "#818CF8",
    "sombra": "rgba(0, 0, 0, 0.45)",
}

COLORES_TARJETAS = ["#7C5CBF", "#F2545B", "#27C28B", "#3B82F6", "#F5A623", "#00B8D9"]

def inyectar_css_global(tema: str = "Oscuro") -> None:
    p = PALETA_OSCURO if tema == "Oscuro" else PALETA_CLARO

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {p['fondo']};
        }}
        [data-testid="stSidebar"] {{
            background-color: {p['tarjeta']};
            border-right: 1px solid {p['borde']};
        }}
        [data-testid="stSidebar"] * {{
            color: {p['texto']};
        }}
        h1, h2, h3, h4, h5, h6, p, span, label, div {{
            color: {p['texto']};
        }}
        [data-testid="stCaptionContainer"] {{
            color: {p['texto_tenue']} !important;
        }}

        /* Métricas nativas (st.metric) con estilo de tarjeta */
        [data-testid="stMetric"] {{
            background: {p['tarjeta']};
            border: 1px solid {p['borde']};
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 1px 4px {p['sombra']};
        }}
        [data-testid="stMetricLabel"] {{
            color: {p['texto_tenue']} !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {p['texto']} !important;
        }}

        /* Pestañas */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: {p['tarjeta']};
            border-radius: 10px 10px 0 0;
            border: 1px solid {p['borde']};
            border-bottom: none;
            padding: 8px 16px;
        }}
        .stTabs [data-baseweb="tab"] p {{
            color: {p['texto']} !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {p['acento']} !important;
        }}
        .stTabs [aria-selected="true"] p {{
            color: white !important;
        }}

        /* Expanders (logs) */
        [data-testid="stExpander"] {{
            background: {p['tarjeta']};
            border: 1px solid {p['borde']};
            border-radius: 12px;
        }}
        [data-testid="stExpander"] summary {{
            color: {p['texto']} !important;
        }}

        /* Bloque de código (visor de logs) */
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCodeBlock"] code {{
            background-color: {p['tarjeta']} !important;
            color: {p['texto']} !important;
            border: 1px solid {p['borde']};
            border-radius: 10px;
        }}

        /* Botones */
        .stButton>button, .stDownloadButton>button {{
            border-radius: 10px;
            border: 1px solid {p['borde']};
            background-color: {p['tarjeta']};
            color: {p['texto']};
        }}

        /* Contenedores con borde (st.container(border=True)) */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px !important;
        }}

        /* -- Inputs nativos (fecha, texto, selects) dentro de .stApp -- */
        .stApp [data-baseweb="input"],
        .stApp [data-baseweb="base-input"],
        .stApp [data-baseweb="select"] > div {{
            background-color: {p['tarjeta']} !important;
            border-color: {p['borde']} !important;
            color: {p['texto']} !important;
        }}
        .stApp [data-baseweb="input"] input,
        .stApp [data-baseweb="select"] input {{
            color: {p['texto']} !important;
        }}
        /* "Pastillas" del multiselect (p. ej. "Lima x") */
        .stApp span[data-baseweb="tag"] {{
            background-color: {p['acento']} !important;
        }}

        /* -- Menús/calendarios en portal (fuera de .stApp): reglas GLOBALES -- */
        div[data-baseweb="popover"] {{
            background-color: {p['tarjeta']} !important;
        }}
        div[data-baseweb="popover"] * {{
            color: {p['texto']} !important;
        }}
        div[data-baseweb="calendar"],
        div[data-baseweb="datepicker"] {{
            background-color: {p['tarjeta']} !important;
        }}
        div[data-baseweb="calendar"] div,
        div[data-baseweb="calendar"] button {{
            background-color: transparent !important;
            color: {p['texto']} !important;
        }}
        ul[role="listbox"], li[role="option"] {{
            background-color: {p['tarjeta']} !important;
            color: {p['texto']} !important;
        }}
        li[role="option"]:hover {{
            background-color: {p['borde']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def colores_grafico() -> dict:
    tema = st.session_state.get("tema_seleccionado", "Oscuro")
    if tema == "Claro":
        return {
            "plot_bgcolor": "#FFFFFF",
            "paper_bgcolor": "#FFFFFF",
            "font_color": "#1F2430",
            "gridcolor": "#E5E7EB",
        }
    return {
        "plot_bgcolor": "#181B22",
        "paper_bgcolor": "#181B22",
        "font_color": "#F5F6FA",
        "gridcolor": "#2A2E38",
    }


def tarjeta_metrica(icono: str, titulo: str, valor: str, color: str, subtitulo: str = "") -> str:
    subtitulo_html = (
        f"<div style='color:rgba(255,255,255,0.85); font-size:0.85rem; margin-top:4px;'>{subtitulo}</div>"
        if subtitulo else ""
    )
    return f"""
    <div style="background:{color}; border-radius:14px; padding:18px 20px;
                box-shadow:0 2px 8px rgba(0,0,0,0.15); min-height:100px;">
        <div style="color:rgba(255,255,255,0.9); font-size:0.95rem; font-weight:600;
                    display:flex; align-items:center; gap:6px;">
            <span style="font-size:1.15rem;">{icono}</span> {titulo}
        </div>
        <div style="color:white; font-size:1.9rem; font-weight:800; margin-top:8px; line-height:1.1;">
            {valor}
        </div>
        {subtitulo_html}
    </div>
    """


def fila_tarjetas(tarjetas: list[dict]) -> None:
    columnas = st.columns(len(tarjetas))
    for i, (col, tarjeta) in enumerate(zip(columnas, tarjetas)):
        color = tarjeta.get("color") or COLORES_TARJETAS[i % len(COLORES_TARJETAS)]
        with col:
            st.markdown(
                tarjeta_metrica(
                    icono=tarjeta.get("icono", ""),
                    titulo=tarjeta.get("titulo", ""),
                    valor=tarjeta.get("valor", ""),
                    color=color,
                    subtitulo=tarjeta.get("subtitulo", ""),
                ),
                unsafe_allow_html=True,
            )
