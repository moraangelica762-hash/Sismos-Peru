# 🌋 Análisis Histórico y Alertas de Sismos en Perú

Data App interactiva construida con **Streamlit** que integra ingesta de datos desde
la API de la **USGS**, validación de esquemas con **Pandera** y visualización con
**Plotly**. El proyecto responde 5 preguntas de negocio sobre la actividad sísmica
histórica de Perú (últimos 50 años) y monitorea alertas recientes.


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

## ❓ Preguntas de negocio respondidas en el dashboard

1. ¿Cómo ha evolucionado la frecuencia de los terremotos en el Perú durante los últimos 50 años?
2. ¿Qué regiones presentan mayor actividad sísmica?
3. ¿Cuál es la distribución de las magnitudes registradas?
4. ¿Existen períodos del año con mayor ocurrencia de sismos?
5. ¿Qué relación existe entre la profundidad y la magnitud de los terremotos?

Además, el dashboard incluye: mapa dinámico con filtros (tiempo, magnitud, profundidad),
tabla de los últimos sismos en Perú, tendencias temporales por región,
histogramas de magnitud/profundidad, panel de alertas recientes y un visor de logs.

---

## 🌎 Zona horaria

Los datos se **almacenan** siempre en UTC (así los entrega la API de la USGS,
y es el estándar para datos sismológicos). Pero todo lo que se **muestra** en
el dashboard (filtros, tabla de últimos sismos, avisos, panel de alertas) usa
**hora de Lima (UTC-5, sin horario de verano)**, para que sea intuitivo para
un usuario en Perú. Esto se resuelve con la columna `fecha_hora_lima`
(`transformacion/procesamiento.py::agregar_hora_local_peru`), calculada a
partir de `fecha_hora_utc` con `zoneinfo` (paquete `tzdata` en
`requirements.txt`, necesario sobre todo en Windows).

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

En Streamlit Cloud la app puede quedar "dormida" si nadie la visita por un
tiempo; al despertar, la primera carga es la que dispara la actualización
(histórica incremental + feeds en vivo), así que siempre queda al día apenas
alguien la abre.

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
git clone https://github.com/<tu-usuario>/<tu-repositorio>.git
cd <tu-repositorio>

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

La app se abre automáticamente en `http://localhost:8501`. El entorno virtual
(`.venv/`) y cualquier archivo `.env` **no se suben a GitHub** (ver `.gitignore`).

---

## 📓 Notebook de análisis (exposición)

El notebook `notebook_analisis/analisis_preguntas_negocio.ipynb` contiene el ciclo
completo (ingesta → exploración → 5 gráficos justificados) usado para generar las
imágenes de la presentación. Para ejecutarlo:

```bash
pip install jupyter matplotlib seaborn statsmodels
jupyter notebook notebook_analisis/analisis_preguntas_negocio.ipynb
```
---

## ☁️ Cómo subir el proyecto a GitHub (paso a paso)

1. Crea una cuenta gratuita en [github.com](https://github.com) si no tienes una.
2. Crea un repositorio nuevo **vacío** (sin README, sin licencia) desde
   [github.com/new](https://github.com/new). Elige visibilidad **Público** para que
   el profesor pueda verlo. Anota la URL, por ejemplo:
   `https://github.com/vares-git/sismos-peru-app.git`
3. En tu computadora, dentro de la carpeta `proyecto_sismos_peru/`, ejecuta:

   ```bash
   git init
   git add .
   git commit -m "Proyecto inicial: Data App de sismos en Perú"
   git branch -M main
   git remote add origin https://github.com/vares-git/sismos-peru-app.git
   git push -u origin main
   ```

4. Verifica en el navegador que todos los archivos aparezcan en GitHub (¡y que
   **no** aparezcan `.venv/` ni `.env`!).
5. Copia la URL del repositorio: la necesitarás para el despliegue en Streamlit
   Cloud y para compartirla con el profesor.

> Si Git te pide usuario/contraseña y falla, GitHub ya no acepta contraseñas por
> HTTPS: crea un *Personal Access Token* en
> `GitHub → Settings → Developer settings → Personal access tokens` y úsalo como
> contraseña, o configura autenticación por SSH.

---

## ☁️ Cómo desplegar en Streamlit Cloud (paso a paso)

1. Asegúrate de que el proyecto ya esté en un repositorio **público** de GitHub
   (paso anterior) y de que `app.py` esté en la **raíz** del repositorio.
2. Entra a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu
   cuenta de GitHub.
3. Haz clic en **"New app"** (o **"Create app"**).
4. Selecciona:
   - **Repository**: `tu-usuario/sismos-peru-app`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. (Opcional) En **"Advanced settings"** puedes fijar la versión de Python (3.10 o
   3.11).
6. Haz clic en **"Deploy"**. Streamlit Cloud instalará `requirements.txt` y
   ejecutará `app.py` automáticamente. El primer despliegue puede tardar unos
   minutos.
7. Cuando termine, obtendrás una URL pública tipo
   `https://sismos-peru-app-<hash>.streamlit.app`. Cópiala y compártela con el
   profesor.
8. Cada vez que hagas `git push` a la rama `main`, Streamlit Cloud vuelve a
   desplegar la app automáticamente.

### Checklist pre-producción

- [x] `requirements.txt` con versiones exactas
- [x] Sin secretos ni credenciales en el código (no hay `.env`)
- [x] `@st.cache_data` en las funciones de carga y transformación
- [x] Manejo de errores con `try/except` en la capa de ingesta y alertas
- [x] `st.spinner` / mensajes de feedback en operaciones lentas
- [x] Código modular con nombres de función en español
- [x] `README.md` con instrucciones de instalación y despliegue
- [x] Probado localmente con `streamlit run app.py`

---

## 🔗 Enlaces del proyecto

- **Repositorio en GitHub:** _completar después de subirlo (paso "Cómo subir a GitHub")_
- **App en Streamlit Cloud:** _completar después de desplegarla (paso "Cómo desplegar en Streamlit Cloud")_

---

## 🧱 Buenas prácticas aplicadas

- Sin carpeta de entorno virtual versionada (`.venv/` en `.gitignore`)
- Sin archivo `.env` en el repositorio
- Código organizado por capas (`ingesta/`, `transformacion/`, `visualizacion/`)
- Nombres de funciones y módulos en español
- Textos, etiquetas, alertas y filtros del dashboard en español
- `requirements.txt` con versiones fijas, probado en un entorno limpio
- Datos validados con Pandera antes de llegar al dashboard
- Logs persistidos en `logs/` y visibles desde el propio dashboard
