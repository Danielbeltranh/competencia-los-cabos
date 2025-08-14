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
.smalllabel {{ color:#334155;font-size:12px;margin-bottom:4px; }}
.info-row {{ margin:8px 0; }}
.info-row .v {{ font-weight:600;font-size:14px;color:{TEXT}; }}
ul.bul {{ margin:6px 0 0 18px; color:{TEXT}; font-size:14px; line-height:1.4; }}
iframe[title^="folium"] {{ scroll-margin-top: 140px; }}
.logo-wrap {{ background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:8px; display:inline-block; }}
.logo-wrap-dark {{ background:#0B132B; border:1px solid #334155; border-radius:12px; padding:10px; display:inline-block; }}
.logo-wrap img, .logo-wrap-dark img {{ max-width:140px; height:auto; display:block; }}
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

def details_card(row):
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
    idx = names.index(st.session_state.selected_name) if st.session_state.selected_name in names else 0
    selected = st.selectbox("Selecciona desarrollo", names, index=idx)
    c1, c2, c3 = st.columns([1,1,2])
    if c1.button("⟵ Anterior", use_container_width=True):
        selected = names[(names.index(selected)-1) % len(names)]
    if c2.button("Siguiente ⟶", use_container_width=True):
        selected = names[(names.index(selected)+1) % len(names)]
    st.session_state.selected_name = selected
    if c3.button("↩ Regresar a Loma escondida", use_container_width=True):
        st.session_state["map_center"] = {"lat": OUR_DEV["lat"], "lon": OUR_DEV["lon"], "zoom": 15}
        st.session_state["center_locked"] = True

    # Selector de tipo de mapa (capas base)
    base_maps = [
        "Esri World Imagery",
        "CartoDB Positron",
        "OpenStreetMap"
    ]
    if "base_choice" not in st.session_state:
        st.session_state["base_choice"] = "Esri World Imagery"
    base_choice = st.selectbox(
        "Tipo de mapa",
        base_maps,
        index=base_maps.index(st.session_state["base_choice"]),
        key="base_choice"
    )

# ================== LAYOUT ==================
left, right = st.columns([1.05, 2.35], gap="large")
with left:
    # === Precios de desarrollos ===
    precios_desarrollos = {
        "Tramonti": ["$267,751", "$531,200"],
        "Casa NIMA": ["$376,950", "$720,300"],
        "Santarena": ["$462,574", "$554,652"],
        "ALANA cerro colorado": ["$385,638", "$494,044"],
        "Vista Vela": ["$460,000", "$495,000"],
        "Dunna": ["$706,000", "$1,211,000"],
        "Solara del Mar": ["$356,000", "$750,000"],
        "Punta Mirante": ["$489,000", "$579,000"],
        "CORA": ["$739,000", "$894,000"],
        "Ladera": ["precio no divulgado por desarrolladora"],
        "MARE": ["precio no divulgado por desarrolladora"]
    }

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
        st.markdown(details_card(sel.iloc[0]), unsafe_allow_html=True)

        # Mostrar precios justo después de los detalles principales
        selected_desarrollo = dev_name
        precios = precios_desarrollos.get(selected_desarrollo, ["precio no divulgado por desarrolladora"])
        if len(precios) == 2:
            st.markdown(f"**Precio desde:** {precios[0]}  ")
            st.markdown(f"**Precio hasta:** {precios[1]}")
        else:
            st.markdown(f"**Precio:** {precios[0]}")

        try:
            d_km = haversine_km(float(sel.iloc[0]["lat"]), float(sel.iloc[0]["lon"]), OUR_DEV["lat"], OUR_DEV["lon"])
            st.info(f"**Distancia a {OUR_DEV['nombre']}:** {d_km:.2f} km")
        except Exception:
            pass

with right:
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
    if st.checkbox("Mostrar línea de distancia a Loma escondida", value=True) and not sel.empty:
        try:
            lat1, lon1 = float(sel.iloc[0]["lat"]), float(sel.iloc[0]["lon"])
            folium.PolyLine([[lat1, lon1], [OUR_DEV["lat"], OUR_DEV["lon"]]],
                            weight=3, color="green",
                            tooltip=f"{haversine_km(lat1, lon1, OUR_DEV['lat'], OUR_DEV['lon']):.2f} km").add_to(m)
        except Exception:
            pass

    # Render del mapa
    ret = st_folium(m, height=780, use_container_width=True, key="map")

    # Mantener selección de marcador si se hizo click
    if ret and ret.get("last_object_clicked_tooltip"):
        st.session_state.selected_name = ret["last_object_clicked_tooltip"]

    try:
        if ret and isinstance(ret.get("last_object_clicked"), dict):
            lat = ret["last_object_clicked"].get("lat", None)
            lng = ret["last_object_clicked"].get("lng", None)
            if lat is not None and lng is not None:
                best_name, best_d = None, 1e9
                for _, r in df.iterrows():
                    try:
                        rlat, rlon = float(r["lat"]), float(r["lon"])
                    except Exception:
                        continue
                    d = haversine_km(lat, lng, rlat, rlon)
                    if d < best_d:
                        best_d, best_name = d, str(r.get("nombre") or "")
                if best_name and best_d <= 0.08 and best_name in names:
                    st.session_state.selected_name = best_name
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

# ================== TABLA ==================
st.markdown("---")
cols_show = ["nombre","tipo_desarrollo","diseno_estilo","estado_desarrollo","num_unidades","tipologias_superficie_m2","amenidades","website"]
present_cols = [c for c in cols_show if c in df.columns]
st.dataframe(df[present_cols], use_container_width=True)