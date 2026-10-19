# 🌋 Análisis Histórico y Alertas de Sismos en Perú

Data App interactiva construida con **Streamlit** que integra ingesta de datos desde
la API de la **USGS**, validación de esquemas con **Pandera** y visualización con
**Plotly**. El proyecto responde 5 preguntas de negocio sobre la actividad sísmica
histórica de Perú (últimos 50 años) y monitorea alertas recientes.

Además incorpora una capa reproducible de **datos no estructurados**, análisis
no supervisado (**K-means + Isolation Forest**), indicadores SMART calculados
desde los datos y un benchmark de volumen. Los modelos describen patrones del
histórico: **no predicen futuros terremotos**.

## 🌐 Acceso público

- **Dashboard:** [Abrir Sismos Perú](https://ku253hjneak74oyvvorabn.streamlit.app/).
- **Código y documentación:** [Ver el repositorio](https://github.com/moraangelica762-hash/Sismos-Peru).

Cualquier persona con estos enlaces puede consultar el proyecto sin iniciar
sesión. Para usar el dashboard en el navegador no es necesario instalar Python
ni descargar el repositorio. Los pasos de instalación siguientes son para
ejecutarlo localmente.

Streamlit puede suspender la app por inactividad; la primera visita puede tardar
en cargar mientras se reactiva.

---

## 📁 Estructura del proyecto

```
Sismos-Peru/
├── app.py                      # Punto de entrada de la Data App
├── main.py                     # Orquestador: corre la ingesta y luego lanza la app localmente
├── requirements.txt            # Dependencias con versiones fijas
├── requirements-dev.txt        # Dependencias para ejecutar las pruebas
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
│   ├── componentes.py          # Sidebar de filtros, panel de alertas, visor de logs
│   ├── analisis_avanzado.py    # Gráficos de clusters y texto
│   └── estilos.py             # Tema visual y tarjetas
├── datos/datos_raw/            # Dataset semilla y metadatos generados al sincronizar
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
  silhouette, evaluado sobre una muestra reproducible de hasta 1 000 eventos
  para acotar la memoria del servidor;
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
si fueran universales. Los volúmenes de prueba se generan repitiendo el dataset
semilla con identificadores nuevos: no representan eventos reales adicionales.
La medición corresponde a la transformación en memoria, sin incluir descarga,
entrenamiento de modelos ni renderizado del dashboard.

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
  2. Si faltan metadatos o han pasado **más de 24 horas desde la última
     sincronización exitosa**, consulta USGS de forma incremental. Usa un
     margen de dos días antes del último evento almacenado para incorporar
     revisiones recientes y deduplica por `id_usgs`.
  3. Registra la consulta exitosa en
     `datos/datos_raw/sismos_peru.metadata.json`, incluso si no llegaron eventos
     nuevos. La antigüedad de un evento no se usa como fecha de sincronización.
  4. Si la sincronización sigue vigente, usa el caché. Ante un fallo de red en
     la actualización incremental, conserva el histórico existente.

  Es decir, **no hay que actualizar el Parquet a mano**: basta con que alguien
  abra la app (o corra `python main.py`) y, si pasaron más de 24h, se
  actualiza sola. Si igual quieres forzarlo ahora mismo, corre en la carpeta
  del proyecto:

  ```bash
  python -c "from ingesta.cliente_usgs import actualizar_incrementalmente; actualizar_incrementalmente()"
  ```

- **Tabla de "Últimos sismos en Perú"**: consulta el IGP y usa USGS como
  respaldo cuando el IGP no responde.
- **Panel de "Alertas recientes"**: consulta USGS y muestra el último reporte
  del IGP como información complementaria.

Las consultas recientes se conservan en caché durante cinco minutos. La app
se refresca cada cinco minutos mientras está abierta, salvo que se active la
opción de pausa. La carga del histórico tiene un caché de una hora; no es una
descarga completa cada cinco minutos ni un proceso que corre permanentemente
cuando la app está cerrada.

---

## 💻 Requisitos

- **Python 3.12**, probado localmente y en Streamlit Community Cloud.
- Git para clonar el repositorio y pip para instalar las dependencias.
- Conexión a internet para instalar dependencias, sincronizar USGS y consultar
  eventos recientes del IGP. El histórico incluido permite trabajar cuando la
  actualización incremental falla; el mapa base también necesita internet.

Para este proyecto, selecciona Python 3.12 en lugar de la versión predeterminada
de Streamlit Cloud: las dependencias fijadas no se han validado con Python 3.13
o 3.14.

---

## 🚀 Instalación y ejecución local

Ejecuta los comandos desde una terminal. En Windows puedes usar PowerShell.

```bash
git clone https://github.com/moraangelica762-hash/Sismos-Peru.git
cd Sismos-Peru
```

Crea un entorno con Python 3.12. Estos comandos usan directamente el Python del
entorno, sin necesidad de activarlo ni cambiar la política de PowerShell.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

**macOS / Linux (con Python 3.12 instalado):**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Como alternativa a `main.py`, ejecuta directamente Streamlit desde la raíz del
repositorio:

```powershell
# Windows
.\.venv\Scripts\python.exe -m streamlit run app.py
```

```bash
# macOS / Linux
.venv/bin/python -m streamlit run app.py
```

La app se abre automáticamente en `http://localhost:8501`. El entorno virtual
(`.venv/`) y cualquier archivo `.env` **no se suben a GitHub** (ver `.gitignore`).

## 🧪 Pruebas y benchmark

`requirements-dev.txt` incluye las dependencias de la aplicación y pytest.
Ejecuta desde la raíz del repositorio:

```powershell
# Windows
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m rendimiento.benchmark_volumen --volumenes 10000 50000 100000
```

```bash
# macOS / Linux
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m rendimiento.benchmark_volumen --volumenes 10000 50000 100000
```

## ☁️ Despliegue en Streamlit Community Cloud

Para crear otro despliegue desde el repositorio público:

1. Inicia sesión en [Streamlit Community Cloud](https://share.streamlit.io/).
2. Selecciona **Create app → Deploy from repo**.
3. Indica el repositorio `moraangelica762-hash/Sismos-Peru`, la rama `main` y el
   archivo principal `app.py`.
4. En **Advanced settings**, selecciona **Python 3.12**.
5. Pulsa **Deploy**. Streamlit instalará `requirements.txt` automáticamente.

El proyecto usa fuentes públicas y no requiere claves API ni secretos para
funcionar. Si el despliegue falla, revisa **Manage app** para consultar el
registro de instalación y ejecución. El despliegue actual está vinculado a
`main` y recibe los cambios publicados en esa rama.

---

## 🔗 Enlaces del proyecto

- **Repositorio en GitHub:** [moraangelica762-hash/Sismos-Peru](https://github.com/moraangelica762-hash/Sismos-Peru)
- **App en Streamlit Cloud:** [Sismos Perú](https://ku253hjneak74oyvvorabn.streamlit.app/)

---
