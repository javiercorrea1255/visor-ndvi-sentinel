import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from datetime import date
import tempfile

# Configuración de la app
st.set_page_config(page_title="Visor NDVI Sentinel-2", layout="wide")
st.title("🌱 Monitor NDVI con Sentinel Hub")
st.markdown("Selecciona una fecha y observa el estado de la vegetación de tu parcela.")

# Parámetros del usuario
fecha = st.date_input("Fecha de análisis", value=date(2024, 6, 1))
visualizar = st.button("Generar mapa NDVI")

# Coordenadas ejemplo (Texcoco, México)
bbox = [-98.885, 19.51, -98.875, 19.52]  # min_lon, min_lat, max_lon, max_lat

# Credenciales Sentinel Hub
CLIENT_ID = "0de3e607-dcd5-4f39-b9e6-6b335909fbdd"
CLIENT_SECRET = "pSg8LroRFf4ybRIdjtAUWDdN0hm6pOrN"
INSTANCE_ID = "b8a3191a-a330-4144-a39f-176ff2578d3c"

@st.cache_data(show_spinner=False)
def obtener_token():
    url = "https://services.sentinel-hub.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("Error al obtener token de acceso.")
        return None

def solicitar_ndvi(fecha, token):
    url = "https://services.sentinel-hub.com/api/v1/process"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{fecha}T00:00:00Z",
                        "to": f"{fecha}T23:59:59Z"
                    }
                }
            }]
        },
        "output": {
            "width": 512,
            "height": 512,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
        },
        "evalscript": """
            //VERSION=3
            function setup() {
              return {
                input: ["B04", "B08"],
                output: { bands: 3 }
              };
            }

            function evaluatePixel(sample) {
              let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
              return [ndvi, ndvi, ndvi];
            }
        """
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        return response.content
    else:
        st.error(f"Error al solicitar NDVI: código {response.status_code}")
        return None

if visualizar:
    st.write("🔄 Procesando imagen NDVI...")
    token = obtener_token()
    if token:
        imagen = solicitar_ndvi(fecha, token)
        if imagen:
            # Convertir imagen binaria a archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(imagen)
                tmp_file.flush()
                temp_image_path = tmp_file.name

            # Crear mapa centrado
            center_lat = (bbox[1] + bbox[3]) / 2
            center_lon = (bbox[0] + bbox[2]) / 2
            m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

            folium.raster_layers.ImageOverlay(
                name="NDVI",
                image=temp_image_path,
                bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
                opacity=0.6
            ).add_to(m)

            folium.LayerControl().add_to(m)
            st_folium(m, width=700, height=500)
