import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen
from folium.features import DivIcon
from streamlit_folium import st_folium

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Mapa Competencia — Los Cabos", layout="wide")

PRIMARY = "#0F766E"   # teal
ACCENT  = "#0EA5A4"
BG_SOFT = "#F6FAF9"
TEXT    = "#0B132B"

# ----------------- HELPERS -----------------
def split_tags(x):
    if not isinstance(x, str) or not x.strip():
        return []
    return [t.strip() for t in x.replace("|", ",").replace(";", ",").split(",") if t.strip()]

def safe(x):  # str safe
    return "" if pd.isna(x) else str(x)

def bullet_list(items):
    if not items:
        return ""
    html = '<ul style="padding-left:20px;margin:0;">'
    for it in items:
        html += f'<li>{it}</li>'
    html += '</ul>'
    return html

def info_row(label, value):
    if not value:
        return ""
    return f"""
    <div style="margin:4px 0;">
      <span style="color:#64748B;font-size:12px;">{label}</span><br/>
      <span style="font-weight:600;font-size:14px;color:{TEXT};">{value}</span>
    </div>
    """

def details_card(row):
    nombre = safe(row.get("nombre"))
    website = safe(row.get("website"))
    tipo = safe(row.get("tipo_desarrollo"))
    estilo = safe(row.get("diseno_estilo"))
    estado = safe(row.get("estado_desarrollo"))
    tipologias = safe(row.get("tipologias_superficie_m2"))
    num_u = safe(row.get("num_unidades"))
    amen = split_tags(safe(row.get("amenidades")))
    servicios = split_tags(safe(row.get("servicios_adicionales")))

    link_html = f'<a href="{website}" target="_blank" style="color:{ACCENT};text-decoration:none;">Ir al sitio ↗</a>' if website else ""

    return f"""
    <div style="background:white;border:1px solid #E2E8F0;border-radius:16px;padding:18px;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0;color:{TEXT};">{nombre}</h3>
        <div>{link_html}</div>
      </div>
      <div style="margin-top:12px;">
        {info_row("Tipo de desarrollo", tipo)}
        {info_row("Estilo / diseño", estilo)}
        {info_row("Estado", estado)}
        {info_row("Tipologías / m²", tipologias)}
        {info_row("Unidades (aprox.)", num_u)}
        <div style="margin-top:10px;">
          <div style="color:#64748B;font-size:12px;margin-bottom:4px;">Amenidades</div>
          {bullet_list(amen)}
        </div>
        <div style="margin-top:10px;">
          <div style="color:#64748B;font-size:12px;margin-bottom:4px;">Servicios</div>
          {bullet_list(servicios)}
        </div>
      </div>
    </div>
    """

# ----------------- DATA -----------------
df = pd.read_csv("competencia_los_cabos.csv", dtype=str)
for c in ["lat","lon"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# columnas mínimas
cols_min = ["nombre","lat","lon","website","tipo_desarrollo","diseno_estilo",
            "estado_desarrollo","tipologias_superficie_m2","num_unidades",
            "amenidades","servicios_adicionales"]
for c in cols_min:
    if c not in df.columns:
        df[c] = ""

df["amenidades"] = df["amenidades"].fillna("")
df["servicios_adicionales"] = df["servicios_adicionales"].fillna("")

# ----------------- UI GLOBAL -----------------
st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; }}
  h3 {{ font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto; }}
</style>
""", unsafe_allow_html=True)

left, right = st.columns([1, 2.2], gap="large")

# ----------------- LEFT PANEL (DETALLES) -----------------
with left:
    st.markdown("###### Selección actual")
    details_placeholder = st.empty()
    # estado de selección (por nombre)
    if "selected_name" not in st.session_state:
        st.session_state.selected_name = "Santarena" if (df["nombre"].str.lower()=="santarena").any() else safe(df.iloc[0]["nombre"])

    sel_name = st.session_state.selected_name
    row_sel = df.loc[df["nombre"]==sel_name].head(1)
    if not row_sel.empty:
        details_placeholder.markdown(details_card(row_sel.iloc[0]), unsafe_allow_html=True)
    else:
        details_placeholder.info("Haz clic en un desarrollo en el mapa para ver detalles.")

    st.markdown("###### Filtros (rápidos)")
    # filtros visuales (opcionales, no afectan selección)
    tipos_all   = sorted([safe(x) for x in df["tipo_desarrollo"].dropna().unique() if safe(x)])
    estilos_all = sorted([safe(x) for x in df["diseno_estilo"].dropna().unique() if safe(x)])
    estados_all = sorted([safe(x) for x in df["estado_desarrollo"].dropna().unique() if safe(x)])

    ft_tipo   = st.multiselect("Tipo", tipos_all)
    ft_estilo = st.multiselect("Estilo / diseño", estilos_all)
    ft_estado = st.multiselect("Estado", estados_all)

# aplicar filtros a la capa (visuales)
mask = pd.Series(True, index=df.index)
if ft_tipo:
    mask &= df["tipo_desarrollo"].isin(ft_tipo)
if ft_estilo:
    mask &= df["diseno_estilo"].isin(ft_estilo)
if ft_estado:
    mask &= df["estado_desarrollo"].isin(ft_estado)
df_map = df[mask].copy()

# ----------------- MAP -----------------
with right:
    # centro: Santarena si existe, si no promedio
    if (df["nombre"].str.lower()=="santarena").any():
        c_row = df.loc[df["nombre"].str.lower()=="santarena"].iloc[0]
        center = [float(c_row["lat"]), float(c_row["lon"])]
    else:
        center = [df["lat"].mean(), df["lon"].mean()]

    tile_options = {
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB Positron": "CartoDB Positron",
        "Esri World Imagery": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    }
    tile_choice = st.selectbox("Mapa base", list(tile_options.keys()))
    tile_url = tile_options[tile_choice]

    if tile_url.startswith("http"):
        m = folium.Map(location=center, zoom_start=15, tiles=tile_url, attr=tile_choice)
    else:
        m = folium.Map(location=center, zoom_start=15, tiles=tile_url)

    Fullscreen(position="topleft", title="Pantalla completa", title_cancel="Salir").add_to(m)

    cluster = MarkerCluster(name="Desarrollos", disableClusteringAtZoom=16).add_to(m)

    # pins + labels
    for _, r in df_map.iterrows():
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except:
            continue

        name = safe(r["nombre"])
        color = "red" if name.strip().lower()=="santarena" else "blue"

        # marker clickable con tooltip (clave para detectar selección)
        folium.Marker(
            [lat, lon],
            tooltip=name,  # lo usamos para identificar el click
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(cluster)

        # label bonito permanente junto al pin
        folium.map.Marker(
            [lat, lon],
            icon=DivIcon(
                icon_size=(150,36),
                icon_anchor=(0,0),
                html=f"""
                <div style="
                    background: rgba(255,255,255,0.9);
                    padding: 2px 8px;
                    border-radius: 8px;
                    border: 1px solid #CBD5E1;
                    color: {TEXT};
                    font-weight: 600;
                    font-size: 12px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
                    transform: translate(10px, -28px);
                    ">
                    {name}
                </div>
                """
            )
        ).add_to(m)

    coords = df_map[["lat","lon"]].dropna().values
    if len(coords):
        m.fit_bounds(coords)

    # render y captura de clics
    st.markdown("### Mapa de competencia — Los Cabos")
    st.caption(f"Proyectos visibles: {len(df_map)} / {len(df)}")
    ret = st_folium(m, height=760, use_container_width=True)

    # si el usuario clickeó un Marker, llega el tooltip del último objeto clickeado
    clicked_name = None
    if ret and "last_object_clicked_tooltip" in ret and ret["last_object_clicked_tooltip"]:
        clicked_name = ret["last_object_clicked_tooltip"]

    if clicked_name:
        st.session_state.selected_name = clicked_name
        row_sel = df.loc[df["nombre"]==clicked_name].head(1)
        if not row_sel.empty:
            details_placeholder.markdown(details_card(row_sel.iloc[0]), unsafe_allow_html=True)

