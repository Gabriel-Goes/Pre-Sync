# -*- coding: utf-8 -*-
"""
rt130_viz.py

Gera figuras (PNG) e legendas automáticas (TXT e TEX) a partir do dicionário `res`
retornado por parse_log.analyze_rt130_log().

Compatível com Python 3.7 e execução headless (matplotlib Agg).

Convenção de saída:
  <out_dir>/<prefix>__<plot_id>.png
  <out_dir>/<prefix>__<plot_id>.caption.txt
  <out_dir>/<prefix>__<plot_id>.caption.tex

Cada função de plot retorna um dict:
  {
    "id": "plot_id",
    "png": "...png",
    "caption_txt": "...txt",
    "caption_tex": "...tex",
  }
"""

import os
from datetime import datetime

import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------------------------
# Helpers de formatação / I/O
# ----------------------------

_LATEX_ESC_MAP = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

def latex_escape(s):
    if s is None:
        return ""
    out = []
    for ch in str(s):
        out.append(_LATEX_ESC_MAP.get(ch, ch))
    return "".join(out)

def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def _fmt_dt(dt):
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)

def _fmt_num(x, nd=2):
    try:
        if x is None:
            return "NA"
        if pd.isna(x):
            return "NA"
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)

def _base_paths(out_dir, prefix, plot_id):
    base = f"{prefix}__{plot_id}" if prefix else plot_id
    png = os.path.join(out_dir, f"{base}.png")
    cap_txt = os.path.join(out_dir, f"{base}.caption.txt")
    cap_tex = os.path.join(out_dir, f"{base}.caption.tex")
    return png, cap_txt, cap_tex

def _write_captions(cap_txt_path, cap_tex_path, caption_text, label=None):
    # TXT “humano”
    with open(cap_txt_path, "w", encoding="utf-8") as f:
        f.write(caption_text.rstrip() + "\n")

    # TEX escapado p/ colar em \caption{...} ou usar \input{...}
    # Aqui escrevemos só o texto (sem \caption), para flexibilidade.
    cap_tex = latex_escape(caption_text).strip()
    if label:
        # opcional: você pode inserir isso dentro de um figure environment
        cap_tex = cap_tex + "\n" + latex_escape(label)

    with open(cap_tex_path, "w", encoding="utf-8") as f:
        f.write(cap_tex.rstrip() + "\n")

def _series_stats(s):
    """
    s: pandas Series com DatetimeIndex.
    Retorna stats básicos + tempo do min/max (útil p/ QC).
    """
    if s is None:
        return None
    s2 = s.dropna()
    if s2.empty:
        return None

    i_min = s2.idxmin()
    i_max = s2.idxmax()

    return {
        "n": int(s2.shape[0]),
        "t0": s2.index.min(),
        "t1": s2.index.max(),
        "min": float(s2.loc[i_min]),
        "max": float(s2.loc[i_max]),
        "t_min": i_min,
        "t_max": i_max,
        "median": float(s2.median()),
        "mean": float(s2.mean()),
    }

def _resample_series(s, freq=None, agg="median"):
    """
    freq: ex "6H" ou None.
    agg: "median", "mean", "min", "max", etc.
    """
    s2 = s.dropna()
    if s2.empty:
        return s2
    if not freq:
        return s2

    r = s2.resample(freq)
    if hasattr(r, agg):
        return getattr(r, agg)()
    return r.agg(agg)

def _plot_timeseries(s, title, ylabel, out_png, figsize=(8.27, 4.2), dpi=150):
    """
    figsize em polegadas. 8.27" ~ largura A4.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.plot(s.index, s.values)
    ax.set_title(title)
    ax.set_xlabel("time")
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

def _plot_bar(x, y, title, xlabel, ylabel, out_png, figsize=(8.27, 4.2), dpi=150):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.bar(x, y)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


# ----------------------------
# Plots + captions (SOH)
# ----------------------------

def plot_battery_voltage(res, out_dir, prefix="", freq=None, agg=None):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_battery_voltage"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or "battery_voltage_v" not in df.columns:
        caption = "Série battery_voltage_v ausente no resultado."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    s_raw = df["battery_voltage_v"].dropna()
    if s_raw.empty:
        caption = "Sem registros de BATTERY VOLTAGE no período (battery_voltage_v vazio após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    # bruto (preserva outliers)
    _plot_timeseries(
        s_raw,
        title=f"Battery voltage (V) — {prefix} (raw samples)" if prefix else "Battery voltage (V) — raw samples",
        ylabel="battery_voltage_v (V)",
        out_png=png,
    )

    st = _series_stats(s_raw)
    caption = (
        "Tensão da bateria principal (BATTERY VOLTAGE) em volts, usando todos os valores amostrados "
        "(sem agregação temporal, preservando outliers). "
        f"N={st['n']} no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],2)} V em {_fmt_dt(st['t_min'])}; "
        f"Máx={_fmt_num(st['max'],2)} V em {_fmt_dt(st['t_max'])}; "
        f"Mediana={_fmt_num(st['median'],2)} V."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_temperature(res, out_dir, prefix="", freq=None, agg=None):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_temperature"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or "temperature_c" not in df.columns:
        caption = "Série temperature_c ausente no resultado."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    s_raw = df["temperature_c"].dropna()
    if s_raw.empty:
        caption = "Sem registros de TEMPERATURE no período (temperature_c vazio após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        s_raw,
        title=f"Temperature (°C) — {prefix} (raw samples)" if prefix else "Temperature (°C) — raw samples",
        ylabel="temperature_c (°C)",
        out_png=png,
    )

    st = _series_stats(s_raw)
    caption = (
        "Temperatura reportada (TEMPERATURE, associada ao bloco BATTERY) em °C, usando todos os valores amostrados "
        "(sem agregação temporal, preservando outliers). "
        f"N={st['n']} no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],1)} °C em {_fmt_dt(st['t_min'])}; "
        f"Máx={_fmt_num(st['max'],1)} °C em {_fmt_dt(st['t_max'])}; "
        f"Mediana={_fmt_num(st['median'],1)} °C."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_backup_voltage(res, out_dir, prefix="", freq=None, agg=None):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_backup_voltage"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or "backup_voltage_v" not in df.columns:
        caption = "Série backup_voltage_v ausente no resultado."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    s_raw = df["backup_voltage_v"].dropna()
    if s_raw.empty:
        caption = "Sem registros de BACKUP no período (backup_voltage_v vazio após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        s_raw,
        title=f"Backup voltage (V) — {prefix} (raw samples)" if prefix else "Backup voltage (V) — raw samples",
        ylabel="backup_voltage_v (V)",
        out_png=png,
    )

    st = _series_stats(s_raw)
    caption = (
        "Tensão do backup (BACKUP) em volts, usando todos os valores amostrados "
        "(sem agregação temporal, preservando outliers). "
        f"N={st['n']} no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],2)} V em {_fmt_dt(st['t_min'])}; "
        f"Máx={_fmt_num(st['max'],2)} V em {_fmt_dt(st['t_max'])}; "
        f"Mediana={_fmt_num(st['median'],2)} V."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

def plot_memory_used_pct(res, out_dir, prefix="", freq="6H", agg="median"):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_memory_used_pct"

    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    needed = {"memory_used_1k", "memory_total_1k"}
    if df is None or not needed.issubset(set(df.columns)):
        caption = "Campos de memória ausentes (necessário: memory_used_1k e memory_total_1k)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    total = df["memory_total_1k"].copy()
    total = total.where(total != 0)
    pct = 100.0 * df["memory_used_1k"] / total

    s = _resample_series(pct, freq=freq, agg=agg)
    if s.empty:
        caption = "Sem registros de memória no período (memory_* vazio após filtragem)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        s,
        title=f"Memory used (%) — {prefix} — {agg}({freq})" if freq else f"Memory used (%) — {prefix}",
        ylabel="used (%)",
        out_png=png,
    )

    st = _series_stats(s)
    caption = (
        "Percentual de memória utilizada, calculado como 100×(memory_used_1k / memory_total_1k), "
        "onde os campos são reportados pelo RT130 em contagens (blocos '1k'). "
        f"Série agregada como {agg} em janelas de {freq}. "
        f"N={st['n']} pontos no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],2)} %, Máx={_fmt_num(st['max'],2)} %, Mediana={_fmt_num(st['median'],2)} %."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_disk_percent_used(res, out_dir, disk_n=1, prefix=""):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = f"soh_disk{disk_n}_used_pct"

    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    used_k = f"disk{disk_n}_used"
    tot_k  = f"disk{disk_n}_total"
    if df is None or used_k not in df.columns or tot_k not in df.columns:
        caption = f"Campos de disco ausentes (necessário: {used_k} e {tot_k})."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    total = df[tot_k].copy()
    total = total.where(total != 0)
    pct = 100.0 * df[used_k] / total
    pct = pct.dropna()
    if pct.empty:
        caption = f"Sem registros de uso do DISK {disk_n} no período (colunas presentes porém sem valores)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        pct,
        title=f"Disk {disk_n} used (%) — {prefix}",
        ylabel="used (%)",
        out_png=png,
    )

    st = _series_stats(pct)
    caption = (
        f"Percentual de ocupação do DISK {disk_n}, calculado como 100×(disk{disk_n}_used / disk{disk_n}_total). "
        "As contagens são as reportadas pelo RT130 nos snapshots de State of Health; "
        "o campo disk*_cluster_k informa o tamanho do cluster (em KiB) quando presente. "
        f"N={st['n']} pontos no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],2)} %, Máx={_fmt_num(st['max'],2)} %, Mediana={_fmt_num(st['median'],2)} %."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

def plot_gps_lat(res, out_dir, prefix=""):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_gps_lat_deg"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or "gps_lat_deg" not in df.columns:
        caption = "Série gps_lat_deg ausente no resultado."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    s = df["gps_lat_deg"].dropna()
    if s.empty:
        caption = "Sem amostras válidas de GPS (gps_lat_deg vazio após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        s,
        title=f"GPS latitude (deg) — {prefix} (raw samples)" if prefix else "GPS latitude (deg) — raw samples",
        ylabel="gps_lat_deg (°)",
        out_png=png,
    )

    st = _series_stats(s)
    caption = (
        "Latitude do GPS (graus decimais), usando todos os valores amostrados. "
        f"N={st['n']} no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],6)}° em {_fmt_dt(st['t_min'])}; "
        f"Máx={_fmt_num(st['max'],6)}° em {_fmt_dt(st['t_max'])}."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_gps_lon(res, out_dir, prefix=""):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_gps_lon_deg"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or "gps_lon_deg" not in df.columns:
        caption = "Série gps_lon_deg ausente no resultado."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    s = df["gps_lon_deg"].dropna()
    if s.empty:
        caption = "Sem amostras válidas de GPS (gps_lon_deg vazio após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    _plot_timeseries(
        s,
        title=f"GPS longitude (deg) — {prefix} (raw samples)" if prefix else "GPS longitude (deg) — raw samples",
        ylabel="gps_lon_deg (°)",
        out_png=png,
    )

    st = _series_stats(s)
    caption = (
        "Longitude do GPS (graus decimais), usando todos os valores amostrados. "
        f"N={st['n']} no intervalo [{_fmt_dt(st['t0'])} .. {_fmt_dt(st['t1'])}]. "
        f"Mín={_fmt_num(st['min'],6)}° em {_fmt_dt(st['t_min'])}; "
        f"Máx={_fmt_num(st['max'],6)}° em {_fmt_dt(st['t_max'])}."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_gps_track(res, out_dir, prefix=""):
    _ensure_dir(out_dir)
    df = res.get("df_soh")
    plot_id = "soh_gps_track_lonlat"
    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    needed = {"gps_lat_deg", "gps_lon_deg"}
    if df is None or not needed.issubset(set(df.columns)):
        caption = "Campos GPS ausentes (necessário: gps_lat_deg e gps_lon_deg)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    g = df[["gps_lon_deg", "gps_lat_deg"]].dropna()
    if g.empty:
        caption = "Sem amostras válidas de GPS (lon/lat vazios após dropna)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    fig, ax = plt.subplots(figsize=(8.27, 4.6), dpi=150)
    ax.scatter(g["gps_lon_deg"].values, g["gps_lat_deg"].values, s=8)
    ax.set_title(f"GPS track (lon/lat) — {prefix} (raw samples)" if prefix else "GPS track (lon/lat) — raw samples")
    ax.set_xlabel("gps_lon_deg (°)")
    ax.set_ylabel("gps_lat_deg (°)")
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)

    lon_min, lon_max = g["gps_lon_deg"].min(), g["gps_lon_deg"].max()
    lat_min, lat_max = g["gps_lat_deg"].min(), g["gps_lat_deg"].max()

    caption = (
        "Dispersão longitude×latitude do GPS (graus decimais), usando todos os valores amostrados. "
        f"N={int(g.shape[0])} no intervalo [{_fmt_dt(g.index.min())} .. {_fmt_dt(g.index.max())}]. "
        f"Envelope: lon=[{_fmt_num(lon_min,6)} .. {_fmt_num(lon_max,6)}], "
        f"lat=[{_fmt_num(lat_min,6)} .. {_fmt_num(lat_max,6)}]."
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


# ----------------------------
# Plots + captions (Eventos)
# ----------------------------

def plot_ev_et_events_hour(res, out_dir, prefix="", top_n=5):
    """
    Distribuição por hora (0..23) dos eventos EH+ET.
    Usa df_evt com index=first_sample (conforme seu analyze_rt130_log).
    """
    _ensure_dir(out_dir)
    df_evt = res.get("df_evt")
    plot_id = "ev_et_events_hour"

    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df_evt is None or df_evt.empty:
        caption = "Sem eventos EH+ET no resultado (df_evt ausente ou vazio)."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    counts = df_evt.groupby(df_evt.index.hour).size()
    # garante 0..23
    counts = counts.reindex(range(24), fill_value=0)

    _plot_bar(
        x=list(counts.index),
        y=list(counts.values),
        title=f"EH+ET events by hour — {prefix}",
        xlabel="hour of day (0..23 - UTM)",
        ylabel="count",
        out_png=png,
    )

    total = int(counts.sum())
    top = counts.sort_values(ascending=False).head(top_n)
    top_str = ", ".join([f"{int(h):02d}h ({int(c)})" for h, c in top.items() if c > 0])

    caption = (
        "Distribuição de eventos (EH combinados com ET) por hora do dia (0–23 UTM), "
        "considerando o timestamp first_sample de cada evento (conforme registrado no log). "
        f"Total={total} eventos no período [{_fmt_dt(df_evt.index.min())} .. {_fmt_dt(df_evt.index.max())}]. "
        + (f"Maiores frequências: {top_str}." if top_str else "Não há horas com contagem > 0.")
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


def plot_soh_events_by_type_hour(res, out_dir, prefix="", top_n_types=6):
    """
    Para eventos extraídos do SOH (df_soh_events, formato long),
    plota (1) total por hora e (2) tipos mais frequentes por hora (stacked simples via múltiplas barras).
    """
    _ensure_dir(out_dir)
    df = res.get("df_soh_events")
    plot_id = "soh_events_by_type_hour"

    png, cap_txt, cap_tex = _base_paths(out_dir, prefix, plot_id)

    if df is None or df.empty or "type" not in df.columns:
        caption = "Sem eventos SOH no resultado (df_soh_events ausente/vazio ou sem coluna 'type')."
        _write_captions(cap_txt, cap_tex, caption)
        return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}

    # top tipos globais
    type_counts = df["type"].value_counts()
    top_types = list(type_counts.head(top_n_types).index)

    # tabela hora x tipo
    df2 = df[df["type"].isin(top_types)].copy()
    hour = df2.index.hour
    tab = pd.crosstab(hour, df2["type"]).reindex(range(24), fill_value=0)

    # plot: barras empilhadas sem controlar cor (matplotlib escolhe defaults)
    fig, ax = plt.subplots(figsize=(8.27, 4.6), dpi=150)
    bottom = None
    x = list(tab.index)
    for col in tab.columns:
        y = tab[col].values
        if bottom is None:
            ax.bar(x, y, label=str(col))
            bottom = y
        else:
            ax.bar(x, y, bottom=bottom, label=str(col))
            bottom = bottom + y

    ax.set_title(f"SOH events by hour (top types) — {prefix}")
    ax.set_xlabel("hour of day (0..23)")
    ax.set_ylabel("count")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)

    total = int(df.shape[0])
    top_type_str = ", ".join([f"{t} ({int(type_counts[t])})" for t in top_types])

    # horas com maior total (somando top_types)
    hour_tot = tab.sum(axis=1).sort_values(ascending=False).head(5)
    hour_tot_str = ", ".join([f"{int(h):02d}h ({int(c)})" for h, c in hour_tot.items() if c > 0])

    caption = (
        "Distribuição dos eventos extraídos do State of Health (SOH) por hora do dia, "
        "agrupando apenas os tipos mais frequentes. "
        f"Total={total} eventos SOH no período [{_fmt_dt(df.index.min())} .. {_fmt_dt(df.index.max())}]. "
        f"Top tipos (contagem total): {top_type_str}. "
        + (f"Horas com maior frequência (somando top tipos): {hour_tot_str}." if hour_tot_str else "")
    )
    _write_captions(cap_txt, cap_tex, caption)
    return {"id": plot_id, "png": png, "caption_txt": cap_txt, "caption_tex": cap_tex}


# ----------------------------
# Orquestrador
# ----------------------------

def plot_all_qc(res, out_dir, prefix="", top_n_evt_types=6):
    _ensure_dir(out_dir)
    items = []

    # Ambientais: BRUTO (preserva outliers)
    items.append(plot_battery_voltage(res, out_dir, prefix=prefix))
    items.append(plot_temperature(res, out_dir, prefix=prefix))
    items.append(plot_backup_voltage(res, out_dir, prefix=prefix))

    # GPS: bruto
    items.append(plot_gps_lat(res, out_dir, prefix=prefix))
    items.append(plot_gps_lon(res, out_dir, prefix=prefix))
    items.append(plot_gps_track(res, out_dir, prefix=prefix))

    # Demais (você decide se quer bruto ou agregado)
    items.append(plot_memory_used_pct(res, out_dir, prefix=prefix, freq="6H", agg="median"))

    items.append(plot_disk_percent_used(res, out_dir, disk_n=1, prefix=prefix))
    items.append(plot_disk_percent_used(res, out_dir, disk_n=2, prefix=prefix))

    items.append(plot_ev_et_events_hour(res, out_dir, prefix=prefix))
    items.append(plot_soh_events_by_type_hour(res, out_dir, prefix=prefix, top_n_types=top_n_evt_types))

    return items
