# 🌋 Análisis Histórico y Alertas de Sismos en Perú

Data App interactiva construida con **Streamlit** que integra ingesta de datos desde
la API de la **USGS**, validación de esquemas con **Pandera** y visualización con
**Plotly**. El proyecto responde 5 preguntas de negocio sobre la actividad sísmica
histórica de Perú (últimos 50 años) y monitorea alertas recientes.

Además incorpora una capa reproducible de **datos no estructurados**, análisis
no supervisado (**K-means + Isolation Forest**), indicadores SMART calculados
desde los datos y un benchmark de volumen. Los modelos describen patrones del
histórico: **no predicen futuros terremotos**.


---

## 📁 Estructura del proyecto

```
proyecto_sismos_peru/
├── app.py                      # Punto de entrada de la Data App
├── main.py                     # Orquestador: corre la ingesta y luego lanza la app localmente
├── requirements.txt            # Dependencias con versiones fijas
├── .gitignore
├── .streamlit/
│   └── config.toml             # Tema visual de la app
├── ingesta/
│   ├── configuracion.py        # Constantes: API, bbox de Perú, rutas, reintentos
│   └── cliente_usgs.py         # Descarga, normaliza y cachea en Parquet
├── transformacion/
│   ├── esquemas.py             # Esquemas de validación con Pandera
│   └── procesamiento.py        # Feature engineering (región, estación, década, etc.)
├── datos_no_estructurados/      # Limpieza y extracción desde descripciones USGS
├── machine_learning/            # Clustering y detección de eventos atípicos
├── indicadores/                 # Indicadores SMART calculados, no declarativos
├── rendimiento/                 # Benchmark reproducible hasta 100 mil filas
├── tests/                       # Pruebas unitarias de las capas nuevas
├── visualizacion/
│   ├── graficos.py             # Los 5 gráficos de preguntas de negocio (Plotly)
│   ├── mapa.py                 # Mapa dinámico de epicentros
│   └── componentes.py          # Sidebar de filtros, panel de alertas, visor de logs
├── datos/datos_raw/            # Caché Parquet (dataset semilla incluido)
├── logs/                       # Logs de ingesta y del dashboard
├── notebook_analisis/          # Notebook de exposición (5 gráficos, independientes del dashboard)
│   ├── analisis_preguntas_negocio.ipynb
│   └── imagenes_graficos/
```

## ❓ Preguntas de negocio que responde el dashboard

1. ¿Cómo ha evolucionado la frecuencia de los terremotos en el Perú durante los últimos 50 años?
2. ¿Qué regiones presentan mayor actividad sísmica?
3. ¿Cuál es la distribución de las magnitudes registradas?
4. ¿Existen períodos del año con mayor ocurrencia de sismos?
5. ¿Qué relación existe entre la profundidad y la magnitud de los terremotos?

Además, el dashboard incluye: mapa dinámico con filtros (tiempo, magnitud, profundidad),
tabla de los últimos sismos en Perú, tendencias temporales por región,
histogramas de magnitud/profundidad, panel de alertas recientes, visor de logs y
una pestaña de análisis avanzado.

## 🧠 Ciencia de datos y datos no estructurados

### Pipeline textual

La descripción `place` de USGS es texto libre (por ejemplo, `45 km SW of Ica,
Peru`). `datos_no_estructurados/procesamiento_texto.py`:

1. conserva el texto fuente para trazabilidad;
2. normaliza Unicode, espacios y mayúsculas;
3. extrae distancia y rumbo cuando existe el patrón de referencia USGS;
4. clasifica el contexto descriptivo y mide si el texto es utilizable.

Son reglas explícitas y comprobables. No se usa el texto para inferir riesgo ni
para inventar una ubicación cuando la fuente no la aporta.

### Minería de datos / ML

`machine_learning/modelos.py` estandariza magnitud, profundidad, latitud y
longitud y ejecuta:

- **K-means**: elige entre 2 y 6 clusters mediante el mayor coeficiente
  silhouette;
- **Isolation Forest**: identifica el 2% de eventos con combinaciones más
  atípicas;
- semilla fija (`42`) y límite de 25 000 filas para el entrenamiento, de modo
  que el resultado sea reproducible y la interfaz siga respondiendo con más
  datos.

El dashboard informa tamaño de muestra, silhouette y tasa de anomalías. Estos
resultados sirven para exploración y priorización de revisión; no constituyen
una alerta oficial ni un modelo de predicción sísmica.

## 📦 Evidencia de procesamiento de alto volumen

- Normalización de GeoJSON por lotes de 5 000 eventos.
- Asignación geográfica vectorizada por lotes de 50 000 filas (sin `apply` fila
  por fila).
- Parquet con compresión Zstandard y grupos de 10 000 filas.
- Lectura selectiva por columnas y rango temporal mediante PyArrow.
- Benchmark repetible con 10 000, 50 000 y 100 000 filas:

```bash
python -m rendimiento.benchmark_volumen
```

El benchmark presenta filas procesadas, segundos y filas por segundo. Sus
resultados dependen del equipo, por lo que no se incluyen cifras estáticas como
si fueran universales.

## 🎯 Indicadores SMART

La pestaña **Análisis avanzado** calcula en cada ejecución:

| Indicador | Meta | Horizonte |
|---|---:|---|
| Filas completas en campos críticos | ≥ 95% | Cada actualización |
| IDs USGS duplicados | 0 | Cada actualización |
| Horas desde la última consulta exitosa a USGS | ≤ 48 horas | Revisión diaria |
| Descripciones textuales utilizables | ≥ 90% | Cada actualización |
| Separación de clusters (silhouette) | ≥ 0.20 | Cada ejecución del modelo |

El estado se deriva del dataset visible; si una meta no se cumple, la tabla lo
muestra en vez de ocultarlo.

---

## 🔄 ¿Cómo se actualizan los datos?

El proyecto tiene **dos fuentes de datos, ambas automáticas**, con distinta frecuencia:

- **Dataset histórico (50 años, usado en los 5 gráficos de preguntas de negocio y
  las tendencias)**: se guarda en `datos/datos_raw/sismos_peru.parquet`. En cada
  carga de la app (`cargar_datos_crudos()` en `app.py`), se llama a
  `asegurar_datos_actualizados()` (`ingesta/cliente_usgs.py`), que:
  1. Si el Parquet no existe, corre la ingesta histórica completa (50 años).
  2. Si existe pero el último evento cacheado tiene **más de 24 horas**,
     dispara una **actualización incremental**: solo pide a la USGS los
     eventos nuevos desde esa fecha (mucho más liviano que volver a descargar
     medio siglo de datos) y los fusiona con lo ya cacheado.
  3. Si ya está al día, no hace ninguna petición.

  Es decir, **no hay que actualizar el Parquet a mano**: basta con que alguien
  abra la app (o corra `python main.py`) y, si pasaron más de 24h, se
  actualiza sola. Si igual quieres forzarlo ahora mismo, corre en la carpeta
  del proyecto:

  ```bash
  python -c "from ingesta.cliente_usgs import actualizar_incrementalmente; actualizar_incrementalmente()"
  ```

- **Tabla de "Últimos sismos en Perú" (debajo del mapa) y panel de "Alertas
  recientes"**: son en vivo. Consultan el feed de la USGS con
  `@st.cache_data(ttl=300)` (5 minutos) y la app hace `st_autorefresh` cada 5
  minutos (`app.py`), por lo que se refrescan solas.

---

## 💻 Requisitos

- **Python 3.10, 3.11 o 3.12** (probado con 3.10.12)
- pip
- Conexión a internet (solo necesaria si el Parquet cacheado no existe o para el panel de alertas)

---

## 🚀 Instalación y ejecución local

Estos pasos funcionan igual en Windows, macOS o Linux, y permiten clonar el proyecto
y levantarlo en cualquier computadora.

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

# 2. Crear y activar un entorno virtual
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En macOS / Linux:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el proyecto completo (ingesta + dashboard)
python main.py

# Alternativa: correr solo el dashboard directamente
streamlit run app.py
```

Para instalar dependencias de prueba y verificar la evidencia técnica:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m rendimiento.benchmark_volumen --volumenes 10000 50000 100000
```

La app se abre automáticamente en `http://localhost:8501`. El entorno virtual
(`.venv/`) y cualquier archivo `.env` **no se suben a GitHub** (ver `.gitignore`).

---

## 🔗 Enlaces del proyecto

- **Repositorio en GitHub:** [moraangelica762-hash/Sismos-Peru](https://github.com/moraangelica762-hash/Sismos-Peru)
- **App en Streamlit Cloud:** [sismos-peru-app](https://sismos-peru-app-rvzuufwndrfps97suyyn7k.streamlit.app/)

---
