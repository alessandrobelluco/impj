"""
GanttPro — Resource Workload Analyzer
======================================
App separata dal POC. Parte dalle risorse e analizza il carico di lavoro
globale e nel tempo, con granularità giornaliera e visibilità sull'overlap
tra progetti.

Requisiti:
    pip install streamlit requests pandas plotly numpy

Avvio:
    streamlit run ganttpro_workload.py
"""

from __future__ import annotations

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta


# ── Costanti ─────────────────────────────────────────────────────────────────
BASE_URL      = "https://api.ganttpro.com/v1.0"
DAILY_CAP_H   = 8.0          # soglia overload (ore/giorno)
WORK_DAYS     = "1111100"    # lun-ven (formato numpy busday)
image_link ='https://github.com/alessandrobelluco/impj/blob/main/Workload_GanttPro/logo_impj.png?raw=True'

#try:
#API_KEY = st.secrets["api_key"]
    
#except KeyError:
API_KEY = st.text_input("API Key", type="password")
if not API_KEY:
    st.warning('Inserire API_KEY Gantt Pro')
    st.stop()

st.set_page_config(
    page_title="GanttPro Workload",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette blu/grigio (niente colori vivaci tranne la heatmap) ───────────────
PROJ_PALETTE = [
    "#1f4e79", "#2e75b6", "#5ba3d9", "#9dc3e6",
    "#404040", "#707070", "#a0a0a0", "#c8c8c8",
    "#14375a", "#3d6fa8", "#7bafd4", "#b8d4ea",
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("GanttPro Workload")
    #password = st.text_input('Inserire password', type='password')
    #if password != st.secrets['psw']:
        #st.error('Password errata')
        #st.stop()
    
    st.caption("Analisi del carico di lavoro per risorsa, con visibilità cross-progetto.")

    st.divider()
    resource_type = st.radio(
        "Tipo risorsa analizzata",
        ["Risorsa Interna", "Fornitore"],
        horizontal=True,
    )
    if resource_type == "Risorsa Interna":
        daily_cap = st.number_input(
            "Soglia overload (ore/giorno)",
            min_value=1.0, max_value=24.0, value=DAILY_CAP_H, step=0.5,
        )
        proj_cap = None
    else:
        proj_cap = st.number_input(
            "Max task gestibili contemporaneamente",
            min_value=1, max_value=50, value=5, step=1,
        )
        daily_cap = None
    include_weekends = st.checkbox("Includi weekend nel calcolo", value=False)

    st.divider()
    load_btn = st.button("Carica tutti i dati", use_container_width=True, type="primary")
    if st.button("Svuota cache", use_container_width=True):
        for k in ["raw_projects", "raw_resources", "raw_tasks", "df_assignments"]:
            st.session_state.pop(k, None)
        st.rerun()



HEADERS = {"X-API-KEY": API_KEY}
WEEKMASK = "Mon Tue Wed Thu Fri Sat Sun" if include_weekends else "Mon Tue Wed Thu Fri"


# ── Helper: chiamate API ──────────────────────────────────────────────────────
def _get(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS,
                         params=params or {}, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError:
        st.warning(f"HTTP {r.status_code} su {path}: {r.text[:200]}")
    except Exception as e:
        st.warning(f"Errore {path}: {e}")
    return None


def _to_list(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "members", "data"):
            if k in data:
                return data[k]
        return [data]
    return []


# ── Helper: ID ────────────────────────────────────────────────────────────────
def _pid(p: dict):
    for k in ("projectId", "id"):
        v = p.get(k)
        if v is not None:
            return str(v)
    return None


def _rid(r: dict):
    for k in ("resourceId", "id"):
        v = r.get(k)
        if v is not None:
            return str(v)
    return None


def _tid(t: dict):
    for k in ("taskId", "id"):
        v = t.get(k)
        if v is not None:
            return str(v)
    return None


# ── Caricamento dati ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_all(api_key_hash: str):
    """Carica projects → resources per project → tasks per project.
    Restituisce (projects_list, resource_catalog, tasks_list).
    resource_catalog: dict resourceId → {name, type, projects:[...]}
    tasks_list: lista di task arricchiti con projectId e projectName
    """
    # 1. Progetti
    raw = _get("/projects")
    if raw is None:
        return None, {}, []
    projects = _to_list(raw)

    resource_catalog: dict[str, dict] = {}
    all_tasks: list[dict] = []

    progress_bar = st.progress(0, text="Caricamento progetti...")
    n = len(projects)

    for i, proj in enumerate(projects):
        pid  = _pid(proj)
        pname = proj.get("name", f"Progetto {pid}")
        progress_bar.progress((i + 1) / n, text=f"Caricamento: {pname}")

        # 2. Risorse del progetto
        res_raw = _get("/resources", params={"projectId": pid})
        for res in _to_list(res_raw):
            rid   = _rid(res)
            rname = res.get("name") or res.get("resourceName") or f"Risorsa {rid}"
            rtype = res.get("type", "unknown")
            if rid:
                if rid not in resource_catalog:
                    resource_catalog[rid] = {"name": rname, "type": rtype, "projects": []}
                if pname not in resource_catalog[rid]["projects"]:
                    resource_catalog[rid]["projects"].append(pname)

        # 3. Task del progetto
        task_raw = _get("/tasks", params={"projectId": pid})
        for task in _to_list(task_raw):
            task["_projectId"]   = pid
            task["_projectName"] = pname
            all_tasks.append(task)

    progress_bar.empty()
    return projects, resource_catalog, all_tasks


# ── Espansione giornaliera ────────────────────────────────────────────────────
def build_daily_assignments(tasks: list, resource_catalog: dict,
                             weekmask: str) -> pd.DataFrame:
    """
    Per ogni task con risorse assegnate, distribuisce le ore equamente
    sui giorni lavorativi compresi tra startDate e endDate.

    Colonne output:
        date, risorsa, resource_id, tipo_risorsa,
        progetto, task, ore, task_id
    """
    rows = []

    for task in tasks:
        pname     = task.get("_projectName", "?")
        tname     = task.get("name", "?")
        tid       = _tid(task)
        duration  = task.get("duration", 0) or 0         # minuti
        resources = task.get("resources") or task.get("assignments") or []

        # Date
        raw_start = task.get("startDate") or task.get("start_date")
        raw_end   = task.get("endDate")   or task.get("end_date")
        if not raw_start or not raw_end:
            continue

        try:
            # GanttPro può restituire timestamp (ms) o stringa ISO
            if isinstance(raw_start, (int, float)):
                d_start = pd.Timestamp(raw_start, unit="ms").date()
                d_end   = pd.Timestamp(raw_end,   unit="ms").date()
            else:
                d_start = pd.to_datetime(raw_start).date()
                d_end   = pd.to_datetime(raw_end).date()
        except Exception:
            continue

        if d_end < d_start:
            d_end = d_start

        # Giorni lavorativi del task
        bdays = np.busday_count(d_start, d_end + timedelta(days=1),
                                weekmask=weekmask)
        bdays = max(bdays, 1)

        # Genera lista di date lavorative
        all_days = pd.bdate_range(
            start=d_start, end=d_end,
            freq="C", weekmask=weekmask,
        ).date.tolist()
        if not all_days:
            all_days = [d_start]

        for r in resources:
            if not isinstance(r, dict):
                continue
            rid         = str(r.get("resourceId") or r.get("id") or "")
            res_val_min = r.get("resourceValue") or 0
            ore_totali  = res_val_min / 60
            ore_per_day = ore_totali / len(all_days)

            # Risolvi nome dalla catalog
            catalog_entry = resource_catalog.get(rid, {})
            rname = (catalog_entry.get("name")
                     or r.get("name") or r.get("resourceName")
                     or f"Risorsa {rid}")
            rtype = catalog_entry.get("type", "unknown")

            for d in all_days:
                rows.append({
                    "date":         d,
                    "risorsa":      rname,
                    "resource_id":  rid,
                    "tipo_risorsa": rtype,
                    "progetto":     pname,
                    "task":         tname,
                    "task_id":      tid,
                    "ore":          round(ore_per_day, 3),
                })

    if not rows:
        return pd.DataFrame(columns=["date","risorsa","resource_id",
                                     "tipo_risorsa","progetto","task","task_id","ore"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CARICAMENTO
# ══════════════════════════════════════════════════════════════════════════════
if load_btn or "df_assignments" not in st.session_state:
    with st.spinner("Connessione a GanttPro..."):
        projects, resource_catalog, all_tasks = load_all(API_KEY[:8])

    if projects is None:
        st.error("Impossibile caricare i progetti. Verifica la API Key.")
        st.stop()

    if not all_tasks:
        st.warning("Nessun task trovato.")
        st.stop()

    with st.spinner("Espansione giornaliera assegnazioni..."):
        df = build_daily_assignments(all_tasks, resource_catalog, WEEKMASK)

    st.session_state["df_assignments"]   = df
    st.session_state["resource_catalog"] = resource_catalog
    st.session_state["projects"]         = projects
    st.session_state["all_tasks"]        = all_tasks

df: pd.DataFrame         = st.session_state.get("df_assignments", pd.DataFrame())
resource_catalog: dict   = st.session_state.get("resource_catalog", {})
projects: list           = st.session_state.get("projects", [])
all_tasks: list          = st.session_state.get("all_tasks", [])

if df.empty:
    st.info("Premi **🚀 Carica tutti i dati** per iniziare.")
    st.stop()


# ── Filtri globali (sidebar) ──────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.subheader("Filtri")

    all_risorse = sorted(df["risorsa"].unique())
    sel_risorse = st.multiselect("Risorse", all_risorse, default=all_risorse,
                                 placeholder="Tutte")

    all_progetti = sorted(df["progetto"].unique())
    sel_progetti = st.multiselect("Progetti", all_progetti, default=all_progetti,
                                  placeholder="Tutti")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    # max_value non limitato: l'utente può estendere il range nel futuro
    date_range = st.date_input("Intervallo date",
                               value=(min_date, max_date),
                               min_value=min_date)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d_from, d_to = date_range
    else:
        d_from, d_to = min_date, max_date

# Applica filtri
mask = (
    df["risorsa"].isin(sel_risorse if sel_risorse else all_risorse) &
    df["progetto"].isin(sel_progetti if sel_progetti else all_progetti) &
    (df["date"] >= pd.Timestamp(d_from)) &
    (df["date"] <= pd.Timestamp(d_to))
)
dff = df[mask].copy()

# ── Calcolo overload centralizzato ───────────────────────────────────────────
# Interna  → valore giornaliero = ore; soglia = daily_cap
# Fornitore → valore giornaliero = n° commesse attive; soglia = proj_cap
is_internal = resource_type == "Risorsa Interna"

if is_internal:
    cap_value = daily_cap
    cap_label = f"{daily_cap} h/giorno"
    cap_unit  = "ore"
    # Serie (risorsa, date) → ore totali
    daily_load = dff.groupby(["risorsa", "date"])["ore"].sum()
else:
    cap_value = proj_cap
    cap_label = f"{proj_cap} task contemporanee"
    cap_unit  = "task"
    # Serie (risorsa, date) → n° task distinte
    daily_load = dff.groupby(["risorsa", "date"])["task_id"].nunique()

# Bool (risorsa, date) → True se in overload quel giorno
overload_mask = daily_load > cap_value


# ── Header metriche ───────────────────────────────────────────────────────────
h_sx, h_dx = st.columns([3,1])

h_sx.title("GanttPro — Workload Analyzer")
h_dx.image(image_link)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Progetti",   len(dff["progetto"].unique()))
c2.metric("Risorse",    len(dff["risorsa"].unique()))
c3.metric("Task",       len(dff["task_id"].unique()))
c4.metric("Ore totali", f"{dff['ore'].sum():.0f} h")

overloaded = overload_mask.groupby(level=0).any().sum()
c5.metric("Risorse in overload", int(overloaded),
          help=f"Almeno un giorno con >{cap_label}")


# ══════════════════════════════════════════════════════════════════════════════
# RIEPILOGO
# ══════════════════════════════════════════════════════════════════════════════

# ── Parametri comuni di allineamento ─────────────────────────────────────
x_min = dff["date"].min()
x_max = dff["date"].max()
x_pad = pd.Timedelta(hours=12)
x_range = [x_min - x_pad, x_max + x_pad]

# Calcola il margine sinistro in base alla label Y più lunga tra i tre grafici.
# Heatmap: nomi risorsa; Gantt: "Commessa — Task"; Bar: nessuna label Y lunga.
_heatmap_labels = list(dff["risorsa"].unique())
_gantt_labels   = [
    f"{row['progetto']}  —  {row['task']}"
    for _, row in dff.groupby(["progetto", "task"]).size().reset_index().iterrows()
]
_max_chars = max((len(s) for s in _heatmap_labels + _gantt_labels), default=20)
_L = max(160, int(_max_chars * 7.2))   # ~7.2 px per carattere (font ~12px)

MARGIN = dict(l=_L, r=220, t=30, b=50)
XAXIS  = dict(range=x_range, tickformat="%d %b", tickangle=-45)

# Legenda ancorata fuori a destra (stessa posizione per Gantt e barre)
LEGEND = dict(x=1.02, y=1, xanchor="left", yanchor="top", title="Progetto")

# ── Heatmap ───────────────────────────────────────────────────────────────
heat_unit = "Ore/gg" if is_internal else "Task/gg"
hover_fmt = ".1f" if is_internal else ".0f"

if is_internal:
    daily_agg_s = dff.groupby(["risorsa", "date"])["ore"].sum().reset_index()
    daily_agg_s.rename(columns={"ore": "_val"}, inplace=True)
else:
    daily_agg_s = dff.groupby(["risorsa", "date"])["task_id"].nunique().reset_index()
    daily_agg_s.rename(columns={"task_id": "_val"}, inplace=True)

st.subheader(f"Carico giornaliero per risorsa ({heat_unit})")

pivot_s = daily_agg_s.pivot_table(
    index="risorsa", columns="date",
    values="_val", aggfunc="sum", fill_value=0,
)
pivot_s = pivot_s.loc[pivot_s.sum(axis=1).sort_values(ascending=False).index]

# Colorscale con cambio netto alla soglia:
# sotto cap_value → verde, sopra cap_value → rosso.
# Con zmax = cap_value * 2, la soglia cade esattamente a 0.5.
_zmax = cap_value * 2 + 0.0001  # epsilon: cap_value esatto mappa a 0.4999969 < 0.4999999
_heat_colorscale = [
    [0.0,        "#e8f5e9"],   # verde chiaro (ok)
    [0.4999999,  "#a5d6a7"],   # verde: breakpoint appena sotto 0.5
    [0.5,        "#e53935"],   # rosso acceso (overload stretto: > cap)
    [1.0,        "#7f0000"],   # rosso scuro (overload pesante)
]

fig_heat_s = go.Figure(data=go.Heatmap(
    z=pivot_s.values,
    x=pivot_s.columns.tolist(),
    y=pivot_s.index.tolist(),
    colorscale=_heat_colorscale,
    zmin=0,
    zmax=_zmax,
    colorbar=dict(
        title=heat_unit, len=0.8,
        x=1.02, xanchor="left",
        y=1,    yanchor="top",
        thickness=15,
    ),
    hoverongaps=False,
    text=[[f"{v:{hover_fmt}}" if v > 0 else "" for v in row] for row in pivot_s.values],
    hovertemplate="<b>%{y}</b><br>%{x|%Y-%m-%d}<br>%{text}<extra></extra>",
))
fig_heat_s.update_layout(
    height=max(280, len(pivot_s) * 30 + 80),
    margin=MARGIN,
    xaxis=XAXIS,
)
st.plotly_chart(fig_heat_s, use_container_width=True)

# ── Gantt dettagliato per task ────────────────────────────────────────────
st.subheader("Timeline task (dettaglio per task)")

gantt_s = (
    dff.groupby(["risorsa", "task", "progetto"])["date"]
    .agg(start="min", end="max")
    .reset_index()
)
gantt_s["ore_tot"] = (
    dff.groupby(["risorsa", "task", "progetto"])["ore"].sum().values
)
gantt_s["end_excl"] = gantt_s["end"] + pd.Timedelta(days=1)
gantt_s = gantt_s.sort_values(["progetto", "start"]).reset_index(drop=True)
# Etichetta Y univoca: "Commessa — Task"
gantt_s["_y_label"] = gantt_s["progetto"] + "  —  " + gantt_s["task"]

fig_gantt_s = px.timeline(
    gantt_s,
    x_start="start", x_end="end_excl",
    y="_y_label", color="progetto",
    hover_name="task",
    hover_data={"risorsa": True, "ore_tot": ":.1f", "start": True, "end": True, "end_excl": False, "_y_label": False},
    labels={"_y_label": "Task", "risorsa": "Risorsa", "progetto": "Progetto", "ore_tot": "Ore"},
    color_discrete_sequence=PROJ_PALETTE,
)
fig_gantt_s.update_yaxes(autorange="reversed")
fig_gantt_s.update_layout(
    height=max(280, len(gantt_s) * 28 + 100),
    margin=MARGIN,
    legend=LEGEND,
    xaxis=XAXIS,
)
st.plotly_chart(fig_gantt_s, use_container_width=True)

# ── Barre andamento giornaliero del team ──────────────────────────────────
if is_internal:
    bar_title  = "Ore totali team per giorno"
    bar_ylabel = "Ore"
    team_daily_s = (
        dff.groupby(["date", "progetto"])["ore"]
        .sum().reset_index()
        .rename(columns={"ore": "_y"})
    )
    bar_hover_fmt = ".1f"
    bar_hover_suf = "h"
else:
    bar_title  = "Task assegnati per giorno"
    bar_ylabel = "N° Task"
    team_daily_s = (
        dff.groupby(["date", "progetto"])["task_id"]
        .nunique().reset_index()
        .rename(columns={"task_id": "_y"})
    )
    bar_hover_fmt = ".0f"
    bar_hover_suf = " task"

st.subheader(bar_title)

palette = PROJ_PALETTE
progetti_ordinati = sorted(team_daily_s["progetto"].unique())

fig_bar_s = go.Figure()
for i, prog in enumerate(progetti_ordinati):
    df_p = team_daily_s[team_daily_s["progetto"] == prog]
    fig_bar_s.add_trace(go.Bar(
        x=df_p["date"],
        y=df_p["_y"],
        name=prog,
        marker_color=palette[i % len(palette)],
        hovertemplate=(
            "%{x|%d %b}<br>" + prog +
            ": %{y:" + bar_hover_fmt + "}" + bar_hover_suf + "<extra></extra>"
        ),
    ))

if is_internal:
    fig_bar_s.add_hline(
        y=daily_cap * len(dff["risorsa"].unique()),
        line_dash="dot", line_color="#555555",
        annotation_text=f"Soglia team ({daily_cap}h × {len(dff['risorsa'].unique())} risorse)",
        annotation_position="top right",
    )
fig_bar_s.update_layout(
    barmode="stack",
    bargap=0.1,
    margin=MARGIN,
    legend=LEGEND,
    yaxis_title=bar_ylabel,
    xaxis=XAXIS,
)
st.plotly_chart(fig_bar_s, use_container_width=True)
