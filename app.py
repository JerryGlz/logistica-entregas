
# TOKEN_LOCATION_IQ = "pk.687257340f32f012a326a2b48280fccf" 
# MI_LOCAL_DIR = "Cerrada San Giovanni 48, Residencial Senderos, 27018 Torreon, Coahuila" # <--- CONFIGURA TU LOCAL
# MI_WHATSAPP = "526181037087" # <--- TU NÚMERO (Formato: 52 + 10 dígitos)
# MI_IMAGEN = st.image("https://cdn-icons-png.flaticon.com/512/3418/3418139.png", width=80)

import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Sistema de Entregas Pro", page_icon="🚗", layout="centered")

# Token y Configuración
TOKEN_LOCATION_IQ = "pk.687257340f32f012a326a2b48280fccf" 
MI_LOCAL_DIR = "Cerrada San Giovanni 48, Residencial Senderos, 27018 Torreon, Coahuila"
MI_WHATSAPP = "526181037087"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1E1E1E; color: white; height: 3.2em; font-weight: bold; border: none; font-size: 0.9em; }
    .wa-button { width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; font-size: 0.9em; margin-top: 5px;}
    .call-button { width:100%; background-color:#007bff; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; font-size: 0.9em; }
    .nav-button { width:100%; background-color:#f39c12; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; font-size: 0.9em; }
    .card-container { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 20px; border-left: 10px solid #3498DB; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .status-done { border-left: 10px solid #2ECC71 !important; background-color: #fafffa !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE NEGOCIO ---
def parse_a_minutos(hora_val):
    try:
        h_str = str(hora_val).strip()[:5]
        t = datetime.strptime(h_str, "%H:%M")
        return t.hour * 60 + t.minute
    except: return 1439

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

def optimizar_ruta(df_in):
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
    
    df_t = pd.DataFrame(resultados)
    ruta = []
    pos = (l_lat, l_lon)
    pend = df_t.copy()
    while not pend.empty:
        deadline = pend['m_fin'].min()
        urg = pend[pend['m_fin'] == deadline].copy()
        urg['dist'] = urg.apply(lambda r: geodesic(pos, (r['lat'], r['lon'])).km if r['geocodificado'] else 999, axis=1)
        idx = urg['dist'].idxmin()
        gan = urg.loc[idx]
        ruta.append(gan)
        if gan['geocodificado']: pos = (gan['lat'], gan['lon'])
        pend = pend.drop(idx)
    return pd.DataFrame(ruta).reset_index(drop=True)

# --- 3. ESTADO DE SESIÓN ---
if 'df_ruta' not in st.session_state:
    st.session_state.df_ruta = None
    st.session_state.entregados = {}
    st.session_state.cam_activa = None

# --- 4. INTERFAZ ---
st.image("https://cdn-icons-png.flaticon.com/512/3418/3418139.png", width=80)
st.title("Sistema de Entregas Optimizado")

archivo = st.file_uploader("📂 Cargar Excel", type=["xlsx", "csv"])

if archivo:
    if st.session_state.df_ruta is None:
        df_raw = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        st.session_state.df_ruta = optimizar_ruta(df_raw)

    for i, row in st.session_state.df_ruta.iterrows():
        num = i + 1
        id_p = f"p_{num}"
        hecho = st.session_state.entregados.get(id_p, False)
        nombre = str(row.get('referencia', f'Parada {num}'))
        
        card_class = "card-container status-done" if hecho else "card-container"
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        # DATOS
        st.markdown(f"### {num}. {nombre}")
        st.markdown(f"📍 {row.get('direccion')}")
        st.markdown(f"🕒 **Ventana:** {row.get('hora_inicio')} - {row.get('hora_fin')}")
        st.markdown(f"👤 **Contacto:** {row.get('contacto', 'S/N')}")
        
        # FILA 1: Mapa y Llamada
        col_nav, col_call = st.columns(2)
        with col_nav:
            q_nav = urllib.parse.quote(f"{nombre} {row.get('direccion')}")
            st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={q_nav}" target="_blank" class="nav-button">🗺️ MAPA</a>', unsafe_allow_html=True)
        with col_call:
            tel = str(row.get('telefono', '')).split('.')[0]
            if tel and tel.lower() not in ['nan', 's/n', '']:
                st.markdown(f'<a href="tel:{tel}" class="call-button">📞 LLAMAR</a>', unsafe_allow_html=True)
            else:
                st.button("📞 SIN TEL", disabled=True, key=f"notel_{num}")

        st.divider()

        # FILA 2: WhatsApp y Foto
        col_wa, col_foto = st.columns(2)
        with col_wa:
            wa_msg = urllib.parse.quote(f"✅ Entrega Confirmada:\n📍 {nombre}\n🏠 {row.get('direccion')}")
            st.markdown(f'<a href="https://wa.me/{MI_WHATSAPP}?text={wa_msg}" target="_blank" class="wa-button">📲 WHATSAPP</a>', unsafe_allow_html=True)
        
        with col_foto:
            label_cam = 'CERRAR' if st.session_state.cam_activa == id_p else '📷 FOTO'
            if st.button(label_cam, key=f"btn_cam_{num}"):
                st.session_state.cam_activa = id_p if st.session_state.cam_activa != id_p else None
                st.rerun()

        # Cámara (Bajo demanda)
        if st.session_state.cam_activa == id_p:
            foto = st.camera_input("Evidencia", key=f"cam_in_{num}")
            if foto:
                st.image(foto)
                st.info("👆 Mantén presionada la foto para guardarla.")

        # Estatus Final
        st.write("")
        if not hecho:
            if st.button(f"✔️ MARCAR ENTREGADO", key=f"done_{num}"):
                st.session_state.entregados[id_p] = True
                st.rerun()
        else:
            if st.button(f"🔄 REABRIR PARADA", key=f"undo_{num}"):
                st.session_state.entregados[id_p] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if st.sidebar.button("🗑️ REINICIAR TODO"):
    st.session_state.clear()
    st.rerun()
