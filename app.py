import os
import math
import pandas as pd
import streamlit as st
import folium
import base64
from streamlit_folium import st_folium

# ================== CONFIG ==================
st.set_page_config(page_title="Mapa competencia — Los Cabos", layout="wide")

ACCENT  = "#0EA5A4"
TEXT    = "#0B132B"

SHOW_LABELS = True  # mostrar etiquetas flotantes sobre cada desarrollo

LOGO_DIR = "static/logos"

# Altura del mapa para evitar scroll brusco
MAP_HEIGHT = 560  # altura del mapa para evitar scroll y encajar en 1 pantalla

# Mapeo de archivos de logo (por nombre de desarrollo -> archivo)
LOGO_FILES = {
    "Santarena": "santarena.png",
    "Dunna": "dunna.png",
    "Ladera San José": "ladera.png",
    "Casa NIMA": "casanima.png",
    "CORA": "cora.png",
    "MARE": "mare.png",
    "Solara del Mar": "solaradelmar.png",
    "Vista Vela": "vistavela.png",
    "Tramonti": "tramonti.png",
    "Punta Mirante": "puntamirante.png",
    "ALANA cerro colorado": "alanacerrocolorado.png",
}

# Correcciones de websites (nombre -> url correcta)
WEBSITE_FIXES = {
    "Solara del Mar": "https://www.inmobiliariafh.com/nuestros-desarrollos/solara-del-mar",
    "Vista Vela": "https://grupovelas.com.mx/desarrollo/vistavela",
    "Tramonti": "https://tramontiparadiso.com/es/inicio/",
    "Punta Mirante": "https://ronival.com/es/punta-mirante/",
}

# === Precios de desarrollos (mapeo global) ===
PRECIOS_DESARROLLOS = {
    "Tramonti": ["$267,751", "$531,200"],
    "Casa NIMA": ["$504,000", "$720,300"],
    "Santarena": ["$466,000", "$554,652"],
    "ALANA cerro colorado": ["$385,638", "$494,044"],
    "Vista Vela": ["$774,000", "$495,000"],
    "Dunna": ["$706,000", "$1,211,000"],
    "Solara del Mar": ["$475,000", "$750,000"],
    "Punta Mirante": ["$628,000", "$579,000"],
    "CORA": ["$476,000", "$894,000"],
    "Ladera": ["875,000", "1,250,000"],
    "MARE": ["$350,000", "$800,000"]
}

# Alias para normalizar nombres que llegan distinto en CSV
NAME_ALIASES = {
    "Solara del mar": "Solara del Mar",
    "Vista vela": "Vista Vela",
    "Vistavela": "Vista Vela",
    "Vista Vela Plus": "Vista Vela",
    "Tramonti Paradiso": "Tramonti",
}

WHITE_LOGO_NAMES = {"Casa NIMA", "CORA", "Punta Mirante", "Santarena", "MARE"}

# === Nuestro desarrollo fijo ===
OUR_DEV = {
    "nombre": "Loma escondida",
    "lat": 23.009139,
    "lon": -109.732472
}

st.markdown(f"""
<style>
.block-container {{ padding-top: 0.8rem; }}
.card {{
  background:#FFF;border:1px solid #E2E8F0;border-radius:16px;
  padding:18px;box-shadow:0 1px 6px rgba(0,0,0,0.05);
}}
.card h3 {{ margin:0;color:{TEXT}; }}
.smalllabel {{ color:#334155;font-size:16px;margin-bottom:8px; }}
.info-row {{ margin:8px 0; }}
.v, .info-row .v {{ font-weight:700;font-size:18px;color:{TEXT}; line-height:1.55; }}
ul.bul {{ margin:10px 0 0 22px; color:{TEXT}; font-size:16px; line-height:1.55; }}
iframe[title^="folium"] {{ scroll-margin-top: 180px; outline: none; }}
.logo-wrap {{ background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:8px; display:inline-block; }}
.logo-wrap-dark {{ background:#0B132B; border:1px solid #334155; border-radius:12px; padding:10px; display:inline-block; }}
.logo-wrap img, .logo-wrap-dark img {{ max-width:140px; height:auto; display:block; }}
.map-wrap {{ max-width: 1100px; }}
html, body, [data-testid="stAppViewContainer"] {{ height:100vh; overflow:hidden; }}
</style>
""", unsafe_allow_html=True)

# ================== HELPERS ==================
def split_csv(s: str):
    if not isinstance(s, str) or not s.strip():
        return []
    return [t.strip() for t in s.split(",") if t.strip()]

def safe(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x)

def info_row(label, value):
    if not value: return ""
    return f"""
    <div class="info-row">
      <div class="smalllabel">{label}</div>
      <div class="v">{value}</div>
    </div>
    """

def details_card(row, precios=None):
    nombre = safe(row.get("nombre"))
    website = safe(row.get("website"))
    tipo = safe(row.get("tipo_desarrollo"))
    estilo = safe(row.get("diseno_estilo"))
    estado = safe(row.get("estado_desarrollo"))
    tipologias = safe(row.get("tipologias_superficie_m2"))
    unidades = safe(row.get("num_unidades"))
    amen_list = split_csv(safe(row.get("amenidades")))
    serv_list = split_csv(safe(row.get("servicios_adicionales")))

    link_html = f'<a href="{website}" target="_blank" style="color:{ACCENT};text-decoration:none;">Ir al sitio ↗</a>' if website else ""
    am_ul = "<ul class='bul'>" + "".join([f"<li>{safe(a)}</li>" for a in amen_list]) + "</ul>" if amen_list else "<div class='smalllabel'>—</div>"
    sv_ul = "<ul class='bul'>" + "".join([f"<li>{safe(a)}</li>" for a in serv_list]) + "</ul>" if serv_list else "<div class='smalllabel'>—</div>"

    return f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
        <h3>{nombre}</h3>
        <div>{link_html}</div>
      </div>
      {f"<div class='v' style='margin-top:6px;'>Precio desde: {precios[0]}</div>" if precios and len(precios)==2 else (f"<div class='v' style='margin-top:6px;'>Precio: {precios[0]}</div>" if precios else "")}
      
      {info_row("Tipo de desarrollo", tipo)}
      {info_row("Estilo / diseño", estilo)}
      {info_row("Estado", estado)}
      {info_row("Tipologías / m²", tipologias)}
      {info_row("Unidades", unidades)}
      <div style="margin-top:8px;">
        <div class="smalllabel">Amenidades</div>
        {am_ul}
      </div>
      <div style="margin-top:8px;">
        <div class="smalllabel">Servicios</div>
        {sv_ul}
      </div>
    </div>
    """

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dlat = p2 - p1
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ================== DATA ==================
fname_candidates = ["competencia_los_cabos_completa.csv", "competencia_los_cabos.csv"]
csv_file = next((f for f in fname_candidates if os.path.exists(f)), None)
if not csv_file:
    st.error("No encontré el CSV de competencia en la carpeta del proyecto.")
    st.stop()

df = pd.read_csv(csv_file, dtype=str).fillna("")
need_cols = [
    "nombre","website","tipo_desarrollo","diseno_estilo","estado_desarrollo",
    "tipologias_superficie_m2","num_unidades","amenidades","servicios_adicionales",
    "lat","lon","logo"
]
for c in need_cols:
    if c not in df.columns: df[c] = ""
df[need_cols] = df[need_cols].astype(str)

# Aplicar correcciones de websites
if "website" in df.columns:
    df["website"] = df.apply(lambda r: WEBSITE_FIXES.get(str(r.get("nombre", "")), str(r.get("website", ""))), axis=1)

# Completar ruta de logo si falta
if "logo" not in df.columns:
    df["logo"] = ""

def _compute_logo_path(row):
    name_raw = str(row.get("nombre", "")).strip()
    name = NAME_ALIASES.get(name_raw, name_raw)
    logo_cell = str(row.get("logo", "")).strip()
    # Si ya viene ruta en CSV, respétala
    if logo_cell:
        # Si es URL externa
        if logo_cell.startswith("http://") or logo_cell.startswith("https://"):
            return logo_cell
        # Ruta relativa local
        return os.path.join(LOGO_DIR, os.path.basename(logo_cell))
    # Si no hay en CSV, intenta por mapeo
    fname = LOGO_FILES.get(name, "")
    if fname:
        return os.path.join(LOGO_DIR, fname)
    return ""

df["logo_path"] = df.apply(_compute_logo_path, axis=1)

names = df["nombre"].astype(str).tolist()

# ================== Persistent map state ==================
if "map_center" not in st.session_state:
    st.session_state["map_center"] = {"lat": 23.0, "lon": -109.73, "zoom": 11}
if "center_locked" not in st.session_state:
    st.session_state["center_locked"] = False
if "last_selected_name" not in st.session_state:
    st.session_state["last_selected_name"] = ""

# ================== HEADER + SELECTOR ==================
if "selected_name" not in st.session_state:
    st.session_state.selected_name = names[0] if names else ""

tcol1, tcol2 = st.columns([2, 3], vertical_alignment="center")
with tcol1:
    st.markdown("## Mapa de competencia — Los Cabos")
    st.caption(f"Proyectos: {len(df)}")
with tcol2:
    pass

# ================== LAYOUT ==================
left, right = st.columns([1.2, 2.1], gap="large")

# --- RIGHT column FIRST ---
with right:
    # === Controles alineados con el panel izquierdo ===
    idx = names.index(st.session_state.selected_name) if st.session_state.selected_name in names else 0
    selected = st.selectbox("Selecciona desarrollo", names, index=idx, key="select_dev")
    c1, c2, c3 = st.columns([1,1,2])
    nav_clicked = False
    if c1.button("⟵ Anterior", use_container_width=True):
        selected = names[(names.index(selected)-1) % len(names)]
        nav_clicked = True
    if c2.button("Siguiente ⟶", use_container_width=True):
        selected = names[(names.index(selected)+1) % len(names)]
        nav_clicked = True
    st.session_state.selected_name = selected
    if nav_clicked:
        st.session_state["ignore_next_map_click"] = True
    if c3.button("↩ Regresar a Loma escondida", use_container_width=True):
        st.session_state["map_center"] = {"lat": OUR_DEV["lat"], "lon": OUR_DEV["lon"], "zoom": 15}
        st.session_state["center_locked"] = True

    base_maps = ["Esri World Imagery", "CartoDB Positron", "OpenStreetMap"]
    if "base_choice" not in st.session_state:
        st.session_state["base_choice"] = "Esri World Imagery"
    base_choice = st.selectbox(
        "Tipo de mapa",
        base_maps,
        index=base_maps.index(st.session_state["base_choice"]),
        key="base_choice"
    )

    # Centro y zoom persistentes
    mc = st.session_state.get("map_center", {"lat": 23.0, "lon": -109.73, "zoom": 11})
    center, zoom = [mc["lat"], mc["lon"]], mc["zoom"]

    # === Mapa con selección de base ===
    m = folium.Map(location=center, zoom_start=zoom, control_scale=True)

    # Capas base (solo una visible a la vez)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        name="Esri World Imagery",
        overlay=False, control=True, show=(base_choice == "Esri World Imagery")
    ).add_to(m)

    folium.TileLayer(
        "CartoDB positron",
        name="CartoDB Positron",
        overlay=False, control=True, show=(base_choice == "CartoDB Positron")
    ).add_to(m)

    folium.TileLayer(
        "OpenStreetMap",
        name="OpenStreetMap",
        overlay=False, control=True, show=(base_choice == "OpenStreetMap")
    ).add_to(m)

    folium.LayerControl(position="topleft", collapsed=False).add_to(m)

    # Loma escondida: estrella verde muy visible
    folium.Marker(
        [float(OUR_DEV["lat"]), float(OUR_DEV["lon"])],
        tooltip=str(OUR_DEV["nombre"]),
        icon=folium.Icon(color="green", icon="star", prefix="fa")
    ).add_to(m)

    if SHOW_LABELS:
        from folium.features import DivIcon
        folium.map.Marker(
            [float(OUR_DEV["lat"]), float(OUR_DEV["lon"])],
            icon=DivIcon(
                icon_size=(200, 36), icon_anchor=(0, 0),
                html=f"<div style='background:#FFF;padding:2px 8px;border-radius:8px;border:1px solid #CBD5E1;color:{TEXT};font-weight:700;font-size:12px;transform: translate(10px, -28px);'>{OUR_DEV['nombre']}</div>"
            )
        ).add_to(m)

    # Marcadores de competencia
    for _, r in df.iterrows():
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except Exception:
            continue
        name = str(r.get("nombre") or "")
        if name == OUR_DEV["nombre"]:
            continue
        # marcador principal
        folium.Marker([lat, lon], tooltip=name, icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

        # etiqueta flotante (si está activada)
        if SHOW_LABELS:
            from folium.features import DivIcon
            folium.map.Marker(
                [lat, lon],
                icon=DivIcon(
                    icon_size=(200, 36), icon_anchor=(0, 0),
                    html=f"<div style='background:#FFF;padding:2px 8px;border-radius:8px;border:1px solid #CBD5E1;color:{TEXT};font-weight:600;font-size:12px;transform: translate(10px, -28px);'>{name}</div>"
                )
            ).add_to(m)

    # Línea opcional de distancia
    show_line = st.checkbox("Mostrar línea de distancia a Loma escondida", value=True)
    if show_line:
        sel_tmp = df.loc[df["nombre"] == st.session_state.selected_name].head(1)
        if not sel_tmp.empty:
            try:
                lat1, lon1 = float(sel_tmp.iloc[0]["lat"]), float(sel_tmp.iloc[0]["lon"])
                folium.PolyLine([[lat1, lon1], [OUR_DEV["lat"], OUR_DEV["lon"]]],
                                weight=3, color="green",
                                tooltip=f"{haversine_km(lat1, lon1, OUR_DEV['lat'], OUR_DEV['lon']):.2f} km").add_to(m)
            except Exception:
                pass

    # Render del mapa con max-width y altura controlada
    st.markdown('<div class="map-wrap">', unsafe_allow_html=True)
    ret = st_folium(m, height=MAP_HEIGHT, use_container_width=True, key="map")
    st.markdown('</div>', unsafe_allow_html=True)

    # Selección desde el mapa (un solo click, con "debounce")
    try:
        lc = ret.get("last_object_clicked") if ret else None
        if (not st.session_state.get("ignore_next_map_click")) and isinstance(lc, dict):
            lat = lc.get("lat"); lng = lc.get("lng")
            cur_click = (lat, lng) if (lat is not None and lng is not None) else None
            prev_click = st.session_state.get("last_map_click")
            if cur_click and cur_click != prev_click:
                best_name, best_d = None, 1e9
                for _, r in df.iterrows():
                    try:
                        rlat, rlon = float(r["lat"]), float(r["lon"])
                    except Exception:
                        continue
                    d = haversine_km(lat, lng, rlat, rlon)
                    if d < best_d:
                        best_d, best_name = d, str(r.get("nombre") or "")
                # Umbral generoso de 0.25 km para no exigir doble click
                if best_name and best_d <= 0.25 and best_name in names:
                    st.session_state.selected_name = best_name
                st.session_state["last_map_click"] = cur_click
        # Siempre limpiar el flag tras procesar
        st.session_state["ignore_next_map_click"] = False
    except Exception:
        pass

    # Si cambió el desarrollo seleccionado, recentrar (y desbloquear)
    try:
        cur = st.session_state.get("selected_name", "")
        prev = st.session_state.get("last_selected_name", "")
        if cur and cur != prev:
            row = df.loc[df["nombre"] == cur].head(1)
            if not row.empty:
                try:
                    lat_c = float(row.iloc[0]["lat"])
                    lon_c = float(row.iloc[0]["lon"])
                    st.session_state["map_center"] = {"lat": lat_c, "lon": lon_c, "zoom": 14}
                    st.session_state["center_locked"] = False
                except Exception:
                    pass
            st.session_state["last_selected_name"] = cur
    except Exception:
        pass

# --- LEFT column SECOND ---
with left:
    sel = df.loc[df["nombre"] == st.session_state.selected_name].head(1)
    if not sel.empty:
        # Logo arriba del recuadro con fondo blanco (mejor visibilidad)
        logo_src = str(sel.iloc[0].get("logo_path", "")).strip()
        dev_name_raw = str(sel.iloc[0].get("nombre", "")).strip()
        dev_name = NAME_ALIASES.get(dev_name_raw, dev_name_raw)
        wrap_class = "logo-wrap-dark" if dev_name in WHITE_LOGO_NAMES else "logo-wrap"
        if logo_src:
            img_html = ""
            if logo_src.startswith("http://") or logo_src.startswith("https://"):
                # URL directa
                img_html = f"<img src='{logo_src}' style='width:140px; display:block;'/>"
            else:
                # Archivo local -> embebido en base64 para que funcione en Cloud
                try:
                    path_try = logo_src
                    if not os.path.exists(path_try):
                        # también probar sin prefijo relativo
                        path_try = os.path.join(os.getcwd(), logo_src)
                    with open(path_try, "rb") as f:
                        data = f.read()
                    ext = os.path.splitext(path_try)[1].lower()
                    m = "png" if ext in [".png"] else "jpeg"
                    b64 = base64.b64encode(data).decode("utf-8")
                    img_html = f"<img src='data:image/{m};base64,{b64}' style='width:140px; display:block;'/>"
                except Exception:
                    img_html = ""
            if img_html:
                st.markdown(f"<div class='{wrap_class}'>{img_html}</div>", unsafe_allow_html=True)
        precios = PRECIOS_DESARROLLOS.get(dev_name, ["precio no divulgado por desarrolladora"])
        st.markdown(details_card(sel.iloc[0], precios=precios), unsafe_allow_html=True)

        try:
            d_km = haversine_km(float(sel.iloc[0]["lat"]), float(sel.iloc[0]["lon"]), OUR_DEV["lat"], OUR_DEV["lon"])
            st.info(f"**Distancia a {OUR_DEV['nombre']}:** {d_km:.2f} km")
        except Exception:
            pass

# ================== TABLA ==================
st.markdown("---")
cols_show = ["nombre","tipo_desarrollo","diseno_estilo","estado_desarrollo","num_unidades","tipologias_superficie_m2","amenidades","website"]
present_cols = [c for c in cols_show if c in df.columns]
st.dataframe(df[present_cols], use_container_width=True)