"""Limpieza y extracción de atributos desde descripciones textuales de USGS.

El campo ``place`` de USGS contiene texto libre, por ejemplo
``"45 km SW of Ica, Peru"``. Este módulo conserva el original y crea atributos
auditables con reglas explícitas; no inventa ubicaciones ausentes.
"""

import re
import unicodedata

import pandas as pd


PATRON_REFERENCIA = re.compile(
    r"^\s*(?P<distancia>\d+(?:[.,]\d+)?)\s*km\s+(?P<direccion>[NSEW]{1,3})\s+of\s+",
    flags=re.IGNORECASE,
)


def normalizar_texto(texto: object) -> str:
    """Convierte texto libre a una representación comparable y sin ruido."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFKC", texto).strip().lower()
    return re.sub(r"\s+", " ", texto)


def extraer_referencia_geografica(texto: object) -> tuple[float | None, str | None]:
    """Extrae distancia y rumbo cuando la descripción sigue el patrón USGS."""
    limpio = normalizar_texto(texto)
    coincidencia = PATRON_REFERENCIA.match(limpio)
    if not coincidencia:
        return None, None
    distancia = float(coincidencia.group("distancia").replace(",", "."))
    return distancia, coincidencia.group("direccion").upper()


def clasificar_contexto(texto: object) -> str:
    """Clasifica el tipo de referencia geográfica sin inferir peligrosidad."""
    limpio = normalizar_texto(texto)
    if not limpio:
        return "Sin descripción"
    if "off the coast" in limpio or "near the coast" in limpio:
        return "Costa o mar"
    if PATRON_REFERENCIA.match(limpio):
        return "Distancia a localidad"
    return "Localidad o región"


def enriquecer_textos_sismos(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas del texto y una bandera de trazabilidad."""
    if "lugar" not in df.columns:
        raise ValueError("El DataFrame debe contener la columna textual 'lugar'.")

    resultado = df.copy()
    resultado["texto_lugar_limpio"] = resultado["lugar"].map(normalizar_texto)
    referencias = resultado["lugar"].map(extraer_referencia_geografica)
    resultado["distancia_referencia_km"] = referencias.map(lambda valor: valor[0])
    resultado["direccion_referencia"] = referencias.map(lambda valor: valor[1])
    resultado["contexto_textual"] = resultado["lugar"].map(clasificar_contexto)
    resultado["num_tokens_texto"] = resultado["texto_lugar_limpio"].map(
        lambda texto: len(texto.split()) if texto else 0
    )
    resultado["texto_utilizable"] = resultado["num_tokens_texto"] >= 2
    return resultado
