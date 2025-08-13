import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
# Plugins seguros (opcionalmente activa MarkerCluster/Fullscreen luego)
from folium.plugins import MarkerCluster, Fullscreen

# ================== CONFIG ==================
st.set_page_config(page_title="Mapa competencia — Los Cabos", layout="wide")

ACCENT  = "#0EA5A4"
TEXT    = "#0B132B"

# Desactiva etiquetas HTML flotantes para máxima compatibilidad en Cloud.
SHOW_LABELS = True  # pon True si quieres probar DivIcon (ver nota más abajo)

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

/* Evita que el foco de scroll salte al iframe del mapa */
iframe[title^="folium"] {{ scroll-margin-top: 140px; }}
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

# ================== DATA ==================
fname_candidates = ["competencia_los_cabos_completa.csv", "competencia_los_cabos.csv"]
csv_file = next((f for f in fname_candidates if os.path.exists(f)), None)
if not csv_file:
    st.error("No encontré el CSV de competencia en la carpeta del proyecto.")
    st.stop()

# Leer como str para evitar dtypes raros; convertimos lat/lon a float solo al usar
df = pd.read_csv(csv_file, dtype=str).fillna("")

need_cols = ["nombre","website","tipo_desarrollo","diseno_estilo","estado_desarrollo",
             "tipologias_superficie_m2","num_unidades","amenidades","servicios_adicionales","lat","lon"]
for c in need_cols:
    if c not in df.columns: df[c] = ""
df[need_cols] = df[need_cols].astype(str)

names = df["nombre"].astype(str).tolist()

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
    c1, c2, _ = st.columns([1,1,6])
    if c1.button("⟵ Anterior", use_container_width=True):
        i = names.index(selected); selected = names[(i-1) % len(names)]
    if c2.button("Siguiente ⟶", use_container_width=True):
        i = names.index(selected); selected = names[(i+1) % len(names)]
    st.session_state.selected_name = selected

# ================== LAYOUT ==================
left, right = st.columns([1.05, 2.35], gap="large")

with left:
    sel = df.loc[df["nombre"] == st.session_state.selected_name].head(1)
    if sel.empty:
        st.info("Selecciona un desarrollo o haz clic en el mapa.")
    else:
        st.markdown(details_card(sel.iloc[0]), unsafe_allow_html=True)

with right:
    # Centro del mapa
    center = [23.0, -109.73]; zoom = 11
    if not sel.empty:
        try:
            lat = float(sel.iloc[0]["lat"])
            lon = float(sel.iloc[0]["lon"])
            center, zoom = [float(lat), float(lon)], 14
        except Exception:
            pass

    # Mapa
    m = folium.Map(location=[float(center[0]), float(center[1])], zoom_start=int(zoom), control_scale=True)

    # Capas base con ATRIBUCIÓN válida
    folium.TileLayer("CartoDB positron", name="CartoDB Positron", control=True).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        name="Esri World Imagery"
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors, Humanitarian style",
        name="OSM HOT"
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="Map data: © OpenStreetMap contributors, SRTM | Style: © OpenTopoMap (CC-BY-SA)",
        name="OpenTopoMap"
    ).add_to(m)

    # Plugins seguros
    Fullscreen(position="topleft", title="Pantalla completa", title_cancel="Salir").add_to(m)
    cluster = MarkerCluster(name="Desarrollos", disableClusteringAtZoom=int(16)).add_to(m)

    # Marcadores simples (solo tipos nativos)
    for _, r in df.iterrows():
        try:
            lat = float(r["lat"]); lon = float(r["lon"])
        except Exception:
            continue
        name = str(r.get("nombre") or "")
        is_sel = (name == st.session_state.selected_name)
        color = "red" if is_sel else "blue"
        folium.Marker(
            [float(lat), float(lon)],
            tooltip=name,
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(cluster)

        # --- OPCIONAL: etiquetas sobre el mapa (DivIcon) ---
        if SHOW_LABELS:
            from folium.features import DivIcon
            html = f"""
            <div style="
                background:#FFFFFF;
                padding:2px 8px;
                border-radius:8px;
                border:1px solid #CBD5E1;
                color:{TEXT};
                font-weight:600;
                font-size:12px;
                transform: translate(10px, -28px);
            ">{name}</div>
            """
            folium.map.Marker(
                [float(lat), float(lon)],
                icon=DivIcon(icon_size=(200, 36), icon_anchor=(0, 0), html=str(html))
            ).add_to(m)

    # Fit a todos si no hay seleccionado
    try:
        pts = df[["lat","lon"]].dropna()
        pts_list = [[float(a), float(b)] for a, b in pts.values.tolist()]
        if pts_list and sel.empty:
            m.fit_bounds(pts_list)
    except Exception:
        pass

    ret = st_folium(m, height=780, use_container_width=True, key="map")

    # Selección opcional desde el mapa
    if ret and isinstance(ret.get("last_object_clicked_tooltip"), str):
        clicked = ret["last_object_clicked_tooltip"]
        if clicked in names:
            st.session_state.selected_name = clicked

# ================== VISTA TABLAR ==================
st.markdown("---")
cols_show = ["nombre","tipo_desarrollo","diseno_estilo","estado_desarrollo",
             "num_unidades","tipologias_superficie_m2","amenidades","website"]
present_cols = [c for c in cols_show if c in df.columns]
st.dataframe(df[present_cols], use_container_width=True)
