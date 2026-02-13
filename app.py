
# TOKEN_LOCATION_IQ = "pk.687257340f32f012a326a2b48280fccf" 
# MI_LOCAL_DIR = "Cerrada San Giovanni 48, Residencial Senderos, 27018 Torreon, Coahuila" # <--- CONFIGURA TU LOCAL
# MI_WHATSAPP = "528712690676" # <--- TU NÚMERO (Formato: 52 + 10 dígitos)
# MI_IMAGEN = st.image("https://cdn-icons-png.flaticon.com/512/3418/3418139.png", width=80)

import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Sistema de Entregas", page_icon="🚗", layout="centered")

# --- TOKEN DE LOCATION IQ ---
TOKEN_LOCATION_IQ = "pk.687257340f32f012a326a2b48280fccf" 

# --- CONFIGURACIÓN DE PUNTOS CLAVE ---
MI_LOCAL_DIR = "Cerrada San Giovanni 48, Residencial Senderos, 27018 Torreon, Coahuila" # <--- CONFIGURA TU LOCAL
MI_WHATSAPP = "528712690676" # <--- TU NÚMERO (Formato: 52 + 10 dígitos)

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1E1E1E; color: white; height: 3.5em; font-weight: bold; border: none; }
    .wa-button { width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; margin-top:10px; font-size: 1.1em; }
    .call-button { width:100%; background-color:#007bff; color:white; border:none; padding:10px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; margin-top:5px; margin-bottom:5px; font-size: 0.9em; }
    .card-container { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 20px; border-left: 8px solid #3498DB; }
    .cam-btn>button { background-color: #E67E22 !important; }
    </style>
    """, unsafe_allow_html=True)

col_img, col_tit = st.columns([0.2, 0.8])
with col_img:
    st.image("https://cdn-icons-png.flaticon.com/512/3418/3418139.png", width=70)
with col_tit:
    st.title("Logística de Entregas")

# --- 2. FUNCIONES DE LÓGICA ---
def parse_a_minutos(hora_val):
    try:
        h_str = str(hora_val).strip()[:5]
        t = datetime.strptime(h_str, "%H:%M")
        return t.hour * 60 + t.minute
    except:
        return 1439

def buscar_coords(direccion, referencia=""):
    url = "https://us1.locationiq.com/v1/search.php"
    query = f"{referencia} {direccion}, Comarca Lagunera, Mexico".strip()
    params = {'key': TOKEN_LOCATION_IQ, 'q': query, 'format': 'json', 'limit': 1}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon']), True
    except: pass
    return None, None, False

def optimizar_ruta_final(df_in):
    df_in.columns = [c.lower().strip() for c in df_in.columns]
    l_lat, l_lon, _ = buscar_coords(MI_LOCAL_DIR)
    if not l_lat: l_lat, l_lon = 25.58913, -103.40713
    
    resultados = []
    for _, fila in df_in.iterrows():
        lat, lon, ok = buscar_coords(fila.get('direccion', ''), fila.get('referencia', ''))
        m_fin = parse_a_minutos(fila.get('hora_fin', '23:59'))
        d = fila.to_dict()
        d.update({'lat': lat, 'lon': lon, 'geocodificado': ok, 'm_fin': m_fin})
        resultados.append(d)
    
    df_temp = pd.DataFrame(resultados)
    ruta_ordenada = []
    punto_actual = (l_lat, l_lon)
    pendientes = df_temp.copy()
    while not pendientes.empty:
        deadline_minimo = pendientes['m_fin'].min()
        urgentes = pendientes[pendientes['m_fin'] == deadline_minimo].copy()
        urgentes['dist'] = urgentes.apply(lambda r: geodesic(punto_actual, (r['lat'], r['lon'])).km if r['geocodificado'] else 999, axis=1)
        idx_ganador = urgentes['dist'].idxmin()
        ganador = urgentes.loc[idx_ganador]
        ruta_ordenada.append(ganador)
        if ganador['geocodificado']: punto_actual = (ganador['lat'], ganador['lon'])
        pendientes = pendientes.drop(idx_ganador)
    return pd.DataFrame(ruta_ordenada).reset_index(drop=True)

# --- 3. INTERFAZ DE USUARIO ---
archivo = st.file_uploader("📂 Cargar Excel de Pedidos", type=["xlsx", "csv"])

if archivo:
    if 'df_ruta' not in st.session_state:
        df_raw = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        st.session_state.df_ruta = optimizar_ruta_final(df_raw)
        st.session_state.entregados = {}
        st.session_state.cam_activa = None # Controlar qué cámara está abierta

    for i, row in st.session_state.df_ruta.iterrows():
        num = i + 1
        id_parada = f"parada_{num}"
        hecho = st.session_state.entregados.get(id_parada, False)
        nombre_lugar = str(row.get('referencia', f'Entrega {num}'))
        
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        
        if hecho:
            st.success(f"✅ {num}. {nombre_lugar} - ENTREGADO")
            wa_msg = urllib.parse.quote(f"✅ Confirmación de Entrega:\n📍 Lugar: {nombre_lugar}\n🏠 Dirección: {row.get('direccion')}")
            st.markdown(f'<a href="https://wa.me/{MI_WHATSAPP}?text={wa_msg}" target="_blank" class="wa-button">📲 ENVIAR AVISO WHATSAPP</a>', unsafe_allow_html=True)
        else:
            st.markdown(f"### {num}. {nombre_lugar}")
            st.write(f"📍 {row.get('direccion')}")
            
            c1, c2 = st.columns(2)
            with c1: st.info(f"🕒 Cierra: {row.get('hora_fin')}")
            with c2:
                tel = str(row.get('telefono', '')).split('.')[0]
                if tel and tel.lower() != 'nan':
                    st.markdown(f'<a href="tel:{tel}" class="call-button">📞 Llamar</a>', unsafe_allow_html=True)

            nav_dest = urllib.parse.quote(f"{nombre_lugar} {row.get('direccion')}, Comarca Lagunera")
            st.link_button(f"🗺️ Navegar GPS", f"https://www.google.com/maps/search/?api=1&query={nav_dest}")
            
            st.divider()

            # LÓGICA DE CÁMARA BAJO DEMANDA
            if st.session_state.cam_activa != id_parada:
                if st.button(f"📷 Abrir Cámara para #{num}", key=f"btn_cam_{num}"):
                    st.session_state.cam_activa = id_parada
                    st.rerun()
            else:
                # La cámara solo existe en el DOM si cam_activa coincide con este ID
                foto = st.camera_input(f"Capturar evidencia: {nombre_lugar}", key=f"input_cam_{num}")
                if foto:
                    st.image(foto)
                    if st.button(f"Confirmar Entrega #{num}", key=f"finish_{num}"):
                        st.session_state.entregados[id_parada] = True
                        st.session_state.cam_activa = None # Cerramos la cámara para liberar recursos
                        st.rerun()
                
                if st.button("❌ Cerrar Cámara", key=f"cancel_{num}"):
                    st.session_state.cam_activa = None
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if st.sidebar.button("🗑️ Limpiar y Reiniciar"):
    st.session_state.clear()
    st.rerun()
