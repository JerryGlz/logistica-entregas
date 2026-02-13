
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
st.set_page_config(page_title="Sistema de Entregas Optimizado", page_icon="🚗", layout="centered")

# --- TOKEN DE LOCATION IQ ---
TOKEN_LOCATION_IQ = "pk.687257340f32f012a326a2b48280fccf" 

# --- DIRECCIÓN DEL PUNTO DE PARTIDA (Comentado para edición rápida) ---
MI_LOCAL_DIR = "Cerrada San Giovanni 48, Residencial Senderos, 27018 Torreon, Coahuila"

# --- TELÉFONO PARA NOTIFICACIONES WHATSAPP ---
MI_WHATSAPP = "528712690676" 

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1E1E1E; color: white; height: 3.5em; font-weight: bold; border: none; }
    .wa-button { width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; margin-bottom:10px; }
    .call-button { width:100%; background-color:#007bff; color:white; border:none; padding:10px; border-radius:10px; font-weight:bold; text-align:center; text-decoration:none; display:inline-block; margin-top:5px; margin-bottom:5px; font-size: 0.9em; }
    .card-container { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 15px; border-left: 6px solid #3498DB; }
    .ios-instruction { background-color: #FFF3CD; color: #856404; padding: 10px; border-radius: 5px; font-size: 0.85em; margin-bottom: 10px; border: 1px solid #ffeeba; }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([0.2, 0.8])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3418/3418139.png", width=80)
with col2:
    st.title("Sistema de Entregas")

# --- 2. FUNCIONES DE APOYO ---
def parse_a_minutos(hora_val):
    try:
        h_str = str(hora_val).strip()
        t = datetime.strptime(h_str[:5], "%H:%M")
        return t.hour * 60 + t.minute
    except:
        return 1439

def buscar_coords(direccion, referencia=""):
    url = "https://us1.locationiq.com/v1/search.php"
    query_busqueda = f"{referencia} {direccion}, Comarca Lagunera, Mexico".strip()
    params = {'key': TOKEN_LOCATION_IQ, 'q': query_busqueda, 'format': 'json', 'limit': 1}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon']), True
    except: pass
    return None, None, False

def optimizar_ruta_final(df_in):
    df_in.columns = [c.lower().strip() for c in df_in.columns]
    l_lat, l_lon, _ = buscar_coords("Los Pensadores 3820, Residencial los Fresnos, Torreon")
    if not l_lat: l_lat, l_lon = 25.58913, -103.40713

    resultados = []
    with st.spinner("📍 Calculando secuencia óptima..."):
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
        urgentes['dist'] = urgentes.apply(
            lambda r: geodesic(punto_actual, (r['lat'], r['lon'])).km if r['geocodificado'] else 999, axis=1
        )
        idx_ganador = urgentes['dist'].idxmin()
        ganador = urgentes.loc[idx_ganador]
        ruta_ordenada.append(ganador)
        if ganador['geocodificado']: punto_actual = (ganador['lat'], ganador['lon'])
        pendientes = pendientes.drop(idx_ganador)
    return pd.DataFrame(ruta_ordenada).reset_index(drop=True)

# --- 3. INTERFAZ ---
archivo = st.file_uploader("📂 Cargar Excel", type=["xlsx", "csv"])

if archivo:
    if 'df_ruta' not in st.session_state:
        df_raw = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        st.session_state.df_ruta = optimizar_ruta_final(df_raw)
        st.session_state.entregados = {}

    for i, row in st.session_state.df_ruta.iterrows():
        num = i + 1
        id_chk = f"chk_{num}"
        hecho = st.session_state.entregados.get(id_chk, False)
        
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        if hecho:
            st.success(f"✅ {num}. {row.get('referencia', 'Entrega')} - COMPLETADO")
        else:
            nombre_lugar = row.get('referencia', 'Sin Referencia')
            st.markdown(f"### {num}. {nombre_lugar}")
            st.markdown(f"📍 {row.get('direccion')}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"🕒 **Ventana:** {row.get('hora_inicio')} - {row.get('hora_fin')}")
            with c2:
                tel = str(row.get('telefono', '')).split('.')[0]
                if tel and tel.lower() != 'nan':
                    st.markdown(f'<a href="tel:{tel}" class="call-button">📞 Llamar</a>', unsafe_allow_html=True)

            q = urllib.parse.quote(f"{nombre_lugar} {row.get('direccion', '')}, Comarca Lagunera")
            st.link_button(f"🗺️ Navegar a Parada {num}", f"https://www.google.com/maps/search/?api=1&query={q}")
            
            if st.checkbox("Confirmar Entrega", key=id_chk):
                foto = st.camera_input("Capturar Evidencia", key=f"cam_{num}")
                if foto:
                    # Instrucción visual para iOS
                    st.markdown("""
                        <div class="ios-instruction">
                        📸 <b>Para guardar la evidencia:</b> Mantén presionada la foto de abajo y selecciona <b>"Guardar en Fotos"</b>.
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.image(foto, use_column_width=True) # Muestra la foto fija para el gesto de iOS
                    
                    if st.button("Finalizar y Avisar ➡️", key=f"confirm_{num}"):
                        st.session_state.entregados[id_chk] = True
                        wa_msg = urllib.parse.quote(f"✅ Entregado en: {nombre_lugar}\n📍 {row.get('direccion')}")
                        url_wa = f"https://wa.me/{MI_WHATSAPP}?text={wa_msg}"
                        st.markdown(f'<a href="{url_wa}" target="_blank" class="wa-button">📲 AVISAR WHATSAPP</a>', unsafe_allow_html=True)
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if st.sidebar.button("🗑️ Reiniciar Sesión"):
    st.session_state.clear()
    st.rerun()
