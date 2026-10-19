import pandas as pd

from datos_no_estructurados.procesamiento_texto import (
    enriquecer_textos_sismos,
    extraer_referencia_geografica,
    normalizar_texto,
)


def test_normaliza_y_extrae_descripcion_usgs():
    assert normalizar_texto("  45 KM   SW of Ica, Peru ") == "45 km sw of ica, peru"
    assert extraer_referencia_geografica("45 km SW of Ica, Peru") == (45.0, "SW")


def test_pipeline_textual_conserva_original_y_maneja_nulos():
    entrada = pd.DataFrame({"lugar": ["Near the coast of Peru", None]})
    salida = enriquecer_textos_sismos(entrada)
    assert salida.loc[0, "lugar"] == "Near the coast of Peru"
    assert salida.loc[0, "contexto_textual"] == "Costa o mar"
    assert not bool(salida.loc[1, "texto_utilizable"])
