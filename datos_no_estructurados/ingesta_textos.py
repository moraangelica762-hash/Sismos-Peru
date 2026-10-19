"""Adaptador entre la respuesta GeoJSON de USGS y el pipeline de texto."""

import pandas as pd

from datos_no_estructurados.procesamiento_texto import enriquecer_textos_sismos


def extraer_descripciones_geojson(features: list[dict]) -> pd.DataFrame:
    """Extrae el identificador y los campos textuales sin alterar el JSON fuente."""
    registros = []
    for feature in features:
        propiedades = feature.get("properties") or {}
        registros.append(
            {
                "id_usgs": feature.get("id"),
                "lugar": propiedades.get("place"),
                "titulo_usgs": propiedades.get("title"),
                "tipo_evento_texto": propiedades.get("type"),
            }
        )
    columnas = ["id_usgs", "lugar", "titulo_usgs", "tipo_evento_texto"]
    return enriquecer_textos_sismos(pd.DataFrame(registros, columns=columnas))
