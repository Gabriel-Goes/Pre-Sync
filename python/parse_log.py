#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_log.py — RT130 (rt2ms log) → estruturas para QC + plots + tabelas (LaTeX)

Objetivo
--------
1) Parsear o log (rt2ms) em blocos "dados_raw" (SH, SC, OM, DS, AD, CD, FD, EH, ET).
2) Normalizar State-of-Health (SOH) em snapshots por timestamp (dados_model["soh"]).
3) Combinar eventos EH+ET em uma tabela (dados_model["events"]).
4) Gerar DataFrames prontos para:
   - plots de séries/contagens ao longo do tempo (resample, histogramas, etc.)
   - tabelas para LaTeX (via to_latex / export .tex / export .csv)

Observações
-----------
- Datas/tempos no log do RT130 são tipicamente UTC; os datetimes aqui são "naive".
- Compatível com Python 3.7 e pandas antigo (não usa pd.NA).
"""

import re
import os
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pprint import pprint



# -----------------------------------------------------------
# Regex: cabeçalho rt2ms
# -----------------------------------------------------------

# Ex:
# "SH exp 00 bytes 0859 2025:310:18:02:08:000000 ID: 9775 seq 0000"
HEADER_RE = re.compile(
    r'^(?P<kind>[A-Z]{2})\s+exp\s+(?P<exp>\d+)\s+bytes\s+(?P<bytes>\d+)\s+'
    r'(?P<time>\S+)\s+ID:\s+(?P<das>\d+)\s+seq\s+(?P<seq>\d+)'
)

# Linha SOH com timestamp no início:
# "310:19:00:00 BATTERY VOLTAGE = 14.2V, TEMPERATURE = 16C, BACKUP = 03.3V"
SOH_LINE_TS_RE = re.compile(
    r'^(?P<jday>\d{3}):(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})'
    r'(?::(?P<sub>\d{3,6}))?\s+(?P<msg>.*)$'
)

# Timestamp embutido:
# "State of Health  25:338:14:00:00:000   ST: 9775"
SOH_EMBED_TS_RE = re.compile(
    r'(?P<yy>\d{2}):(?P<jday>\d{3}):(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}):(?P<ms>\d{3})'
)

# Métricas SOH
BATTERY_RE = re.compile(
    r'BATTERY VOLTAGE\s*=\s*(?P<batt>[0-9.]+)V,\s*'
    r'TEMPERATURE\s*=\s*(?P<temp>[-0-9.]+)C,\s*'
    r'BACKUP\s*=\s*(?P<backup>[0-9.]+)V'
)

GPS_RE = re.compile(
    r'GPS:\s*POSITION:\s*(?P<lat>[NS]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+'
    r'(?P<lon>[EW]\d{3}:\d{2}:\d{2}(?:\.\d+)?)\s+\+(?P<alt>\d+)M'
)

MEM_RE = re.compile(
    r'MEMORY\s+USED=(?P<used>\d+),\s*AVAILABLE=(?P<avail>\d+),\s*TOTAL=(?P<total>\d+)'
)

DISK_RE = re.compile(
    r'^DISK\s+(?P<n>\d+)(?P<active>\*)?\s*:?\s*USED:\s*(?P<used>\d+)\s+'
    r'AVAIL:\s*(?P<avail>\d+)\s+TOTAL:\s*(?P<total>\d+)\s+CL:\s*(?P<cl>\d+)K'
)

BVTC_RE = re.compile(
    r'BVTC\s+BW\s+B:\s*(?P<b_uv>\d+)UV\s+NOM,\s*V:\s*(?P<v_uv>\d+)UV\s+CAL,\s*'
    r'T:\s*(?P<t_mk>[0-9.]+)MK\s+CAL,\s*C:\s*(?P<c_uv>\d+)UV\s+CAL'
)

RTP_SLEEP_RE = re.compile(r'RTP:\s*FORCING DISCOVERY SLEEP FOR:(?P<sec>\d+)\s+SECONDS')


# -----------------------------------------------------------
# Utilidades de tempo RT130
# -----------------------------------------------------------

def parse_rt130_time(time_str):
    """
    Converte 'YYYY:JJJ:HH:MM:SS:USEC' em datetime.
    """
    parts = time_str.split(":")
    if len(parts) != 6:
        raise ValueError("Formato de tempo inesperado: %r" % time_str)
    year = int(parts[0])
    jday = int(parts[1])
    hh = int(parts[2])
    mm = int(parts[3])
    ss = int(parts[4])
    usec = int(parts[5])
    base = datetime(year, 1, 1) + timedelta(days=jday - 1)
    return base.replace(hour=hh, minute=mm, second=ss, microsecond=usec)


def _dt_from_jday(year, jday, h, m, s, micro=0):
    base = datetime(year, 1, 1) + timedelta(days=jday - 1)
    return base.replace(hour=h, minute=m, second=s, microsecond=micro)


def _dms_to_decimal(dms):
    # "N00:00:00.00" / "W046:12:03.2"
    hemi = dms[0].upper()
    sign = -1.0 if hemi in ("S", "W") else 1.0
    parts = dms[1:].split(":")
    deg = float(parts[0]); minute = float(parts[1]); sec = float(parts[2])
    return sign * (deg + minute / 60.0 + sec / 3600.0)


def parse_soh_line_time(line, default_year, header_dt=None):
    """
    Retorna (dt, msg). Se não conseguir formar dt absoluto, usa header_dt.
    """
    s = line.strip()

    m = SOH_LINE_TS_RE.match(s)
    if m:
        gd = m.groupdict()
        year = default_year or (header_dt.year if header_dt else None)
        if year is None:
            return header_dt, gd["msg"].strip()

        jday = int(gd["jday"])
        h = int(gd["h"]); mi = int(gd["m"]); se = int(gd["s"])
        sub = gd.get("sub")
        micro = 0
        if sub:
            micro = int(sub) * 1000 if len(sub) == 3 else int(sub)
        dt = _dt_from_jday(year, jday, h, mi, se, micro)
        return dt, gd["msg"].strip()

    m = SOH_EMBED_TS_RE.search(s)
    if m:
        yy = int(m.group("yy"))
        year = 2000 + yy
        jday = int(m.group("jday"))
        h = int(m.group("h")); mi = int(m.group("m")); se = int(m.group("s"))
        micro = int(m.group("ms")) * 1000
        dt = _dt_from_jday(year, jday, h, mi, se, micro)
        return dt, s

    return header_dt, s


# -----------------------------------------------------------
# Parser: rt2ms log → dados_raw
# -----------------------------------------------------------

def _iter_blocks(lines):
    """
    Quebra o arquivo em blocos separados por linha em branco.
    """
    bloco = []
    for ln in lines:
        if ln.strip() == "":
            if bloco:
                yield "\n".join(bloco)
                bloco = []
        else:
            bloco.append(ln.rstrip("\n"))
    if bloco:
        yield "\n".join(bloco)


def _parse_block(block_text):
    """
    Parse de um bloco genérico (SH, SC, OM, DS, AD, CD, FD, EH, ET).
    """
    linhas = [ln for ln in block_text.splitlines() if ln.strip()]
    if not linhas:
        return None

    header = linhas[0].strip()
    result = {"header": header, "fields": {}}

    m = HEADER_RE.match(header)
    if m:
        gd = m.groupdict()
        result.update(gd)
        result["exp"] = int(result["exp"])
        result["bytes"] = int(result["bytes"])
        result["das"] = int(result["das"])
        result["seq"] = int(result["seq"])
        kind = gd["kind"]
    else:
        kind = header.split()[0]
        if kind.endswith(":"):
            kind = kind[:-1]

    result["kind"] = kind

    extra = []
    for ln in linhas[1:]:
        stripped = ln.strip()

        # "chave = valor" (evita linhas de tempo SH e "DAS: ...")
        if (
            "=" in ln
            and stripped
            and not stripped[0].isdigit()
            and not stripped.startswith("DAS:")
        ):
            key, val = ln.split("=", 1)
            key = key.strip().rstrip("-").strip()
            val = val.strip()
            result["fields"][key] = val
        else:
            extra.append(stripped)

    if extra:
        result["extra_lines"] = extra

    ev = result["fields"].get("event")
    if ev is not None:
        try:
            result["event_id"] = int(ev)
        except ValueError:
            result["event_id"] = ev

    return result


def parse_rt130_log_to_raw(path):
    """
    Lê o log rt2ms e retorna:
      dados_raw["SH"/"SC"/...]: lista de blocos
      dados_raw["EH"/"ET"]: dict event_id -> list de blocos
      dados_raw["OTHER"]: blocos não classificados
    """
    dados_raw = {
        "meta": {},
        "SH": [],
        "SC": [],
        "OM": [],
        "DS": [],
        "AD": [],
        "CD": [],
        "FD": [],
        "EH": defaultdict(list),
        "ET": defaultdict(list),
        "OTHER": [],
    }

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()

    if lines and lines[0].startswith("rt2ms:"):
        meta_line = lines[0]
        dados_raw["meta"]["rt2ms_line"] = meta_line
        m = re.match(r"rt2ms:\s+v(\S+)\s+Run time \(UTC\):\s+(.+)", meta_line)
        if m:
            dados_raw["meta"]["rt2ms_version"] = m.group(1)
            dados_raw["meta"]["run_time_utc"] = m.group(2)
        block_lines = lines[1:]
    else:
        block_lines = lines

    for block_text in _iter_blocks(block_lines):
        parsed = _parse_block(block_text)
        if not parsed:
            continue

        kind = parsed.get("kind")
        if kind in ("SH", "SC", "OM", "DS", "AD", "CD", "FD"):
            dados_raw[kind].append(parsed)
        elif kind in ("EH", "ET"):
            ev_id = parsed.get("event_id")
            if ev_id is None:
                dados_raw["OTHER"].append(parsed)
            else:
                dados_raw[kind][ev_id].append(parsed)
        else:
            dados_raw["OTHER"].append(parsed)

    dados_raw["EH"] = dict(dados_raw["EH"])
    dados_raw["ET"] = dict(dados_raw["ET"])
    return dados_raw


# -----------------------------------------------------------
# SOH normalizado (snapshots por timestamp)
# -----------------------------------------------------------

def apply_soh_message(rec, msg):
    """
    Atualiza rec com métricas parseadas e/ou registra evento.
    Retorna True se a msg foi reconhecida (métrica/evento).
    """
    m = BATTERY_RE.search(msg)
    if m:
        rec["battery_voltage_v"] = float(m.group("batt"))
        rec["temperature_c"] = float(m.group("temp"))
        rec["backup_voltage_v"] = float(m.group("backup"))
        return True

    m = GPS_RE.search(msg)
    if m:
        lat_dms = m.group("lat"); lon_dms = m.group("lon")
        rec["gps_lat_dms"] = lat_dms
        rec["gps_lon_dms"] = lon_dms
        rec["gps_lat_deg"] = _dms_to_decimal(lat_dms)
        rec["gps_lon_deg"] = _dms_to_decimal(lon_dms)
        rec["gps_alt_m"] = int(m.group("alt"))
        return True

    m = MEM_RE.search(msg)
    if m:
        rec["memory_used_1k"] = int(m.group("used"))
        rec["memory_available_1k"] = int(m.group("avail"))
        rec["memory_total_1k"] = int(m.group("total"))
        return True

    m = DISK_RE.match(msg)
    if m:
        n = int(m.group("n"))
        prefix = "disk%d_" % n
        rec[prefix + "active"] = bool(m.group("active"))
        rec[prefix + "used"] = int(m.group("used"))
        rec[prefix + "avail"] = int(m.group("avail"))
        rec[prefix + "total"] = int(m.group("total"))
        rec[prefix + "cluster_k"] = int(m.group("cl"))
        return True

    m = BVTC_RE.search(msg)
    if m:
        rec["bvtc_b_uv_nom"] = int(m.group("b_uv"))
        rec["bvtc_v_uv_cal"] = int(m.group("v_uv"))
        rec["bvtc_t_mk_cal"] = float(m.group("t_mk"))
        rec["bvtc_c_uv_cal"] = int(m.group("c_uv"))
        return True

    # eventos discretos (lista)
    if "EXTERNAL CLOCK POWER IS TURNED" in msg:
        rec.setdefault("events", []).append({
            "type": "external_clock_power",
            "state": "ON" if msg.endswith("ON") else "OFF",
            "msg": msg
        })
        return True

    if msg.startswith("AUTO DUMP"):
        rec.setdefault("events", []).append({"type": "auto_dump", "msg": msg})
        return True

    if msg.startswith("ACQUISITION"):
        rec.setdefault("events", []).append({"type": "acquisition", "msg": msg})
        return True

    if msg.startswith("RTP:"):
        ev = {"type": "rtp", "msg": msg}
        m = RTP_SLEEP_RE.search(msg)
        if m:
            try:
                ev["sleep_s"] = int(m.group("sec"))
            except Exception:
                pass
        rec.setdefault("events", []).append(ev)
        return True

    return False


def build_soh_full(dados_raw):
    """
    Retorna lista ordenada por tempo.
    Cada item = snapshot por timestamp (dt), com métricas opcionais + events/messages.
    """
    by_time = {}  # dt -> rec

    for block in dados_raw.get("SH", []):
        try:
            header_dt = parse_rt130_time(block["time"])
            year = header_dt.year
        except Exception:
            header_dt = None
            year = None

        for line in block.get("extra_lines", []):
            dt, msg = parse_soh_line_time(line, default_year=year, header_dt=header_dt)
            if dt is None:
                continue

            rec = by_time.get(dt)
            if rec is None:
                rec = {"time": dt, "das": block.get("das")}
                by_time[dt] = rec

            rec.setdefault("sh_seq", set()).add(block.get("seq"))

            parsed = apply_soh_message(rec, msg)
            if not parsed:
                rec.setdefault("messages", []).append(msg)

    out = []
    for dt in sorted(by_time.keys()):
        rec = by_time[dt]
        if isinstance(rec.get("sh_seq"), set):
            rec["sh_seq"] = sorted(x for x in rec["sh_seq"] if x is not None)
        out.append(rec)

    return out


# -----------------------------------------------------------
# Eventos (EH + ET)
# -----------------------------------------------------------

def build_events(dados_raw):
    """
    Combina EH+ET por (event_id, stream). Retorna:
      {
        "by_id": {(event, stream): ev_dict, ...},
        "by_time": [ev_dict, ...] ordenado por first_sample
      }
    """
    events_by_id = {}

    index_et = {}
    for ev_id, et_list in dados_raw.get("ET", {}).items():
        for et in et_list:
            f = et.get("fields", {})
            stream_str = f.get("stream")
            if not stream_str:
                continue
            stream = int(stream_str)
            key = (ev_id, stream)
            index_et.setdefault(key, []).append(et)

    def safe_parse_time(s):
        if not s:
            return None
        try:
            return parse_rt130_time(s)
        except Exception:
            return None

    for ev_id, eh_list in dados_raw.get("EH", {}).items():
        for eh in eh_list:
            f_eh = eh.get("fields", {})
            stream_str = f_eh.get("stream")
            if not stream_str:
                continue
            stream = int(stream_str)
            key = (ev_id, stream)

            et_list = index_et.get(key)
            if not et_list:
                continue

            et = et_list[-1]
            f_et = et.get("fields", {})

            try:
                eh_time = parse_rt130_time(eh["time"])
            except Exception:
                eh_time = None

            trigger_time = safe_parse_time(f_eh.get("trigger time") or f_et.get("trigger time"))
            first_sample = safe_parse_time(f_et.get("first sample"))
            last_sample = safe_parse_time(f_et.get("last sample"))

            duration_s = None
            if first_sample and last_sample:
                duration_s = (last_sample - first_sample).total_seconds()

            ns = sps = eto = None
            for line in et.get("extra_lines", []):
                if "NS:" in line and "SPS:" in line:
                    m_ns = re.search(r"NS:\s+(\d+)", line)
                    m_sps = re.search(r"SPS:\s+([0-9.]+)", line)
                    m_eto = re.search(r"ETO:\s+(\d+)", line)
                    if m_ns:
                        ns = int(m_ns.group(1))
                    if m_sps:
                        sps = float(m_sps.group(1))
                    if m_eto:
                        eto = int(m_eto.group(1))
                    break

            sample_rate = None
            if "sample rate" in f_eh:
                try:
                    sample_rate = float(f_eh["sample rate"])
                except Exception:
                    sample_rate = None
            elif "sample rate" in f_et:
                try:
                    sample_rate = float(f_et["sample rate"])
                except Exception:
                    sample_rate = None

            ev_dict = {
                "event": ev_id,
                "stream": stream,
                "stream_name": f_eh.get("stream name"),
                "trigger_type": f_eh.get("trigger type"),
                "sample_rate": sample_rate,
                "eh_time": eh_time,
                "trigger_time": trigger_time,
                "first_sample": first_sample,
                "last_sample": last_sample,
                "duration_s": duration_s,
                "nsamples": ns,
                "sps": sps,
                "eto": eto,
                "seq_eh": eh.get("seq"),
                "seq_et": et.get("seq"),
                "das": eh.get("das", et.get("das")),
                "raw_eh": eh,
                "raw_et": et,
            }

            events_by_id[(ev_id, stream)] = ev_dict

    events_by_time = sorted(events_by_id.values(), key=lambda e: e["first_sample"] or datetime.min)
    return {"by_id": events_by_id, "by_time": events_by_time}


# -----------------------------------------------------------
# Config (SC, OM, DS, AD, CD, FD)
# -----------------------------------------------------------

def _normalize_field_name(name):
    key = name.strip().lower().replace(" ", "_")
    key = re.sub(r"[^0-9a-z_]", "_", key)
    return key


def build_config_table(blocks):
    table = []
    for b in blocks:
        try:
            t = parse_rt130_time(b["time"])
        except Exception:
            t = None

        row = {
            "kind": b.get("kind"),
            "time": t,
            "das": b.get("das"),
            "seq": b.get("seq"),
            "raw": b,
        }
        for k, v in b.get("fields", {}).items():
            row[_normalize_field_name(k)] = v

        table.append(row)

    return table


# -----------------------------------------------------------
# Wrapper: dados_raw → dados_model
# -----------------------------------------------------------

def build_dados_model(dados_raw):
    return {
        "meta": dados_raw.get("meta", {}).copy(),
        "soh": build_soh_full(dados_raw),
        "events": build_events(dados_raw),
        "config": {
            "SC": build_config_table(dados_raw.get("SC", [])),
            "OM": build_config_table(dados_raw.get("OM", [])),
            "DS": build_config_table(dados_raw.get("DS", [])),
            "AD": build_config_table(dados_raw.get("AD", [])),
            "CD": build_config_table(dados_raw.get("CD", [])),
            "FD": build_config_table(dados_raw.get("FD", [])),
        },
    }


# -----------------------------------------------------------
# DataFrames: SOH / SOH-events / SOH-messages / EH+ET events
# -----------------------------------------------------------

def _is_scalar(v):
    return v is None or isinstance(v, (int, float, bool, str))


def _hour_hist_from_index(dt_index):
    import pandas as pd
    if dt_index is None or len(dt_index) == 0:
        return pd.Series([0]*24, index=list(range(24)), dtype="int64")
    h = pd.Series(dt_index.hour)
    return (h.value_counts()
             .reindex(range(24), fill_value=0)
             .sort_index()
             .astype("int64"))


def soh_to_frames(soh, *, drop_gps_zero=True):
    """
    Retorna:
      df_soh     : index=time, colunas=métricas escalares + das + sh_seq
      df_events  : eventos SOH em formato longo
      df_msgs    : mensagens SOH em formato longo
      views      : subconjuntos (batt/mem/gps/disk1/disk2/bvtc)
    """
    import pandas as pd
    import numpy as np

    META_KEYS = {"time", "das", "sh_seq", "messages", "events"}

    rows = []
    ev_rows = []
    msg_rows = []

    for r in soh:
        t = r["time"]
        das = r.get("das")
        sh_seq = tuple(r.get("sh_seq", []))

        row = {"time": t, "das": das, "sh_seq": sh_seq}
        for k, v in r.items():
            if k in META_KEYS:
                continue
            if _is_scalar(v):
                row[k] = v
        rows.append(row)

        for ev in (r.get("events", []) or []):
            ev_rows.append({
                "time": t,
                "das": das,
                "sh_seq": sh_seq,
                "type": ev.get("type"),
                "state": ev.get("state"),
                "sleep_s": ev.get("sleep_s"),
                "msg": ev.get("msg"),
            })

        for msg in (r.get("messages", []) or []):
            msg_rows.append({
                "time": t,
                "das": das,
                "sh_seq": sh_seq,
                "msg": msg,
            })

    df_soh = pd.DataFrame(rows).sort_values("time").set_index("time")

    for c in df_soh.columns:
        if c in ("das", "sh_seq"):
            continue
        df_soh[c] = pd.to_numeric(df_soh[c], errors="ignore")

    # limpeza GPS 0,0,0 (mantém dms em None; deg/alt em nan)
    gps_cols = ["gps_lat_deg", "gps_lon_deg", "gps_alt_m"]
    if drop_gps_zero and all(c in df_soh.columns for c in gps_cols):
        mask0 = (df_soh["gps_lat_deg"] == 0) & (df_soh["gps_lon_deg"] == 0) & (df_soh["gps_alt_m"] == 0)
        if mask0.any():
            df_soh.loc[mask0, gps_cols] = np.nan
            for c in ("gps_lat_dms", "gps_lon_dms"):
                if c in df_soh.columns:
                    df_soh.loc[mask0, c] = None

    df_events = (pd.DataFrame(ev_rows).sort_values("time").set_index("time")
                 if ev_rows else pd.DataFrame(columns=["das","sh_seq","type","state","sleep_s","msg"]))

    df_msgs = (pd.DataFrame(msg_rows).sort_values("time").set_index("time")
               if msg_rows else pd.DataFrame(columns=["das","sh_seq","msg"]))

    def _safe_cols(cols):
        return [c for c in cols if c in df_soh.columns]

    df_batt = df_soh[_safe_cols(["battery_voltage_v", "backup_voltage_v", "temperature_c"])].dropna(how="all")
    df_mem  = df_soh[_safe_cols(["memory_used_1k", "memory_available_1k", "memory_total_1k"])].dropna(how="all")
    df_gps  = df_soh[_safe_cols(["gps_lat_deg", "gps_lon_deg", "gps_alt_m", "gps_lat_dms", "gps_lon_dms"])].dropna(how="all")
    df_bvtc = df_soh[_safe_cols(["bvtc_b_uv_nom", "bvtc_v_uv_cal", "bvtc_t_mk_cal", "bvtc_c_uv_cal"])].dropna(how="all")
    df_disk1 = df_soh.filter(regex=r"^disk1_").dropna(how="all")
    df_disk2 = df_soh.filter(regex=r"^disk2_").dropna(how="all")

    views = {
        "batt": df_batt,
        "mem": df_mem,
        "gps": df_gps,
        "bvtc": df_bvtc,
        "disk1": df_disk1,
        "disk2": df_disk2,
    }

    return df_soh, df_events, df_msgs, views


def events_model_to_frame(events_model):
    """
    events_model = dados_model["events"] (EH+ET)
    Retorna df_evt index=first_sample (quando existir).
    """
    import pandas as pd
    rows = []
    for e in (events_model.get("by_time") or []):
        rows.append({
            "first_sample": e.get("first_sample"),
            "last_sample": e.get("last_sample"),
            "trigger_time": e.get("trigger_time"),
            "event": e.get("event"),
            "stream": e.get("stream"),
            "stream_name": e.get("stream_name"),
            "trigger_type": e.get("trigger_type"),
            "sample_rate": e.get("sample_rate"),
            "duration_s": e.get("duration_s"),
            "nsamples": e.get("nsamples"),
            "sps": e.get("sps"),
            "eto": e.get("eto"),
            "das": e.get("das"),
        })

    if not rows:
        return pd.DataFrame(columns=[
            "last_sample","trigger_time","event","stream","stream_name","trigger_type",
            "sample_rate","duration_s","nsamples","sps","eto","das"
        ])

    df_evt = pd.DataFrame(rows).sort_values("first_sample").set_index("first_sample")
    return df_evt


# -----------------------------------------------------------
# Métricas QC (tabelas prontas p/ LaTeX)
# -----------------------------------------------------------

def compute_external_clock_stats(df_soh_events):
    """
    Estima duração ON/OFF a partir das transições (diferença entre timestamps).
    Retorna dict com durações (s), frações e estatísticas de intervalos.
    """
    import numpy as np
    if df_soh_events is None or len(df_soh_events) == 0:
        return None

    clk = df_soh_events[df_soh_events.get("type") == "external_clock_power"].copy()
    if len(clk) == 0:
        return None

    clk = clk.sort_index()
    # mapeia state -> 1/0
    def _map_state(s):
        if s == "ON":
            return 1
        if s == "OFF":
            return 0
        return None

    clk["state01"] = [ _map_state(x) for x in clk.get("state") ]
    # diffs
    t = clk.index.to_pydatetime()
    dt_s = []
    for i in range(len(t) - 1):
        dt_s.append((t[i+1] - t[i]).total_seconds())
    # atribui dt ao estado do intervalo (estado na linha i)
    on_s = off_s = 0.0
    for i, dts in enumerate(dt_s):
        st = clk["state01"].iloc[i]
        if st == 1:
            on_s += dts
        elif st == 0:
            off_s += dts

    total = on_s + off_s
    frac_off = (off_s / total) if total > 0 else None
    frac_on = (on_s / total) if total > 0 else None

    # estatística dos intervalos entre eventos (toggle period)
    if dt_s:
        dt_arr = np.array(dt_s, dtype=float)
        stats = {
            "interval_mean_s": float(dt_arr.mean()),
            "interval_median_s": float(np.median(dt_arr)),
            "interval_min_s": float(dt_arr.min()),
            "interval_max_s": float(dt_arr.max()),
        }
    else:
        stats = {}

    out = {
        "n_events": int(len(clk)),
        "on_s": float(on_s),
        "off_s": float(off_s),
        "frac_on": frac_on,
        "frac_off": frac_off,
    }
    out.update(stats)
    return out


def build_qc_tables(*, df_soh, df_batt, df_mem, df_bvtc, df_disk1, df_disk2, df_soh_events, df_evt):
    """
    Retorna dict de DataFrames prontos para LaTeX/CSV:
      - overview
      - battery_stats
      - memory_stats
      - event_types
      - soh_key_coverage
      - external_clock_stats
      - evt_counts_hour (EH+ET)
    """
    import pandas as pd

    tables = {}

    # overview
    t0 = df_soh.index.min() if len(df_soh) else None
    t1 = df_soh.index.max() if len(df_soh) else None
    tables["overview"] = pd.DataFrame([{
        "soh_rows": int(len(df_soh)),
        "time_first": t0,
        "time_last": t1,
        "evt_rows": int(len(df_evt)) if df_evt is not None else 0,
        "soh_events_rows": int(len(df_soh_events)) if df_soh_events is not None else 0,
    }])

    # cobertura por “tema”
    def _cov(df):
        if df is None:
            return 0
        return int(len(df))

    tables["coverage"] = pd.DataFrame([{
        "batt_rows": _cov(df_batt),
        "mem_rows": _cov(df_mem),
        "bvtc_rows": _cov(df_bvtc),
        "disk1_rows": _cov(df_disk1),
        "disk2_rows": _cov(df_disk2),
        "soh_events_rows": _cov(df_soh_events),
        "evt_rows": _cov(df_evt),
    }])

    # battery stats
    if df_batt is not None and len(df_batt):
        desc = df_batt.describe(percentiles=[0.05, 0.5, 0.95]).T
        tables["battery_stats"] = desc
    else:
        tables["battery_stats"] = pd.DataFrame()

    # memory stats (inclui % usado)
    if df_mem is not None and len(df_mem):
        dfm = df_mem.copy()
        if "memory_used_1k" in dfm.columns and "memory_total_1k" in dfm.columns:
            dfm["memory_used_pct"] = (dfm["memory_used_1k"] / dfm["memory_total_1k"]) * 100.0
        tables["memory_stats"] = dfm.describe(percentiles=[0.05, 0.5, 0.95]).T
    else:
        tables["memory_stats"] = pd.DataFrame()

    # eventos SOH por tipo
    if df_soh_events is not None and len(df_soh_events) and "type" in df_soh_events.columns:
        tables["soh_event_types"] = df_soh_events["type"].value_counts().rename("count").to_frame()
    else:
        tables["soh_event_types"] = pd.DataFrame()

    # external clock stats (resumo em 1 linha)
    clk_stats = compute_external_clock_stats(df_soh_events)
    tables["external_clock_stats"] = pd.DataFrame([clk_stats]) if clk_stats else pd.DataFrame()

    # EH+ET: contagens por hora do dia (first_sample)
    if df_evt is not None and len(df_evt):
        hh = _hour_hist_from_index(df_evt.index)
        tables["evt_counts_hour"] = hh.rename("count").to_frame()
    else:
        tables["evt_counts_hour"] = pd.DataFrame()

    return tables


# -----------------------------------------------------------
# Export helpers (CSV + LaTeX)
# -----------------------------------------------------------

def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def export_frames_csv(frames, out_dir, prefix="rt130"):
    """
    frames: dict nome -> DataFrame
    """
    ensure_dir(out_dir)
    for name, df in frames.items():
        if df is None:
            continue
        out = os.path.join(out_dir, "%s_%s.csv" % (prefix, name))
        try:
            df.to_csv(out)
        except Exception:
            # fallback (pandas velho / objetos estranhos)
            df.to_csv(out, encoding="utf-8")


def export_table_latex(df, out_path, *, caption=None, label=None, index=True, escape=False, float_format="%.3f"):
    """
    Exporta tabela LaTeX com wrapper de table+caption+label.
    """
    ensure_dir(os.path.dirname(out_path))
    body = df.to_latex(index=index, escape=escape, float_format=float_format)

    if caption or label:
        lines = []
        lines.append("\\begin{table}[ht]")
        lines.append("\\centering")
        lines.append(body.strip())
        if caption:
            lines.append("\\caption{%s}" % caption)
        if label:
            lines.append("\\label{%s}" % label)
        lines.append("\\end{table}")
        body = "\n".join(lines) + "\n"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)


# -----------------------------------------------------------
# Relatório / análise (p/ IPython)
# -----------------------------------------------------------

def analyze_rt130_log(logfile, *, make_frames=True, verbose=True, drop_gps_zero=True):
    """
    Função principal para IPython:

      from parse_log import analyze_rt130_log
      res = analyze_rt130_log("RT130_....log")
      df_soh = res["df_soh"]
      df_evt = res["df_evt"]
      tables = res["tables"]

    Retorna dict com:
      - dados_raw, dados_model
      - df_soh, df_soh_events, df_soh_msgs, views (batt/mem/gps/disk/bvtc)
      - df_evt (EH+ET)
      - tables (QC tables)
      - diag (keys/frequencies)
    """
    dados_raw = parse_rt130_log_to_raw(logfile)
    dados_model = build_dados_model(dados_raw)

    soh = dados_model.get("soh", [])
    meta = dados_model.get("meta", {})

    META_KEYS = {"time", "das", "sh_seq", "messages", "events"}

    # diagnóstico de chaves (SOH)
    all_keys = set().union(*(r.keys() for r in soh)) if soh else set()
    metric_keys = sorted(all_keys - META_KEYS)

    cnt = Counter()
    for r in soh:
        for k in r.keys():
            if k not in META_KEYS:
                cnt[k] += 1

    suspects = set()
    for r in soh:
        for k, v in r.items():
            if k in META_KEYS:
                continue
            if isinstance(v, (list, dict, set, tuple)):
                suspects.add(k)

    res = {
        "logfile": logfile,
        "dados_raw": dados_raw,
        "dados_model": dados_model,
        "diag": {
            "metric_keys": metric_keys,
            "metric_counts": cnt,
            "suspects": sorted(suspects),
        },
    }

    if make_frames:
        df_soh, df_soh_events, df_soh_msgs, views = soh_to_frames(soh, drop_gps_zero=drop_gps_zero)
        df_evt = events_model_to_frame(dados_model.get("events") or {})
        tables = build_qc_tables(
            df_soh=df_soh,
            df_batt=views.get("batt"),
            df_mem=views.get("mem"),
            df_bvtc=views.get("bvtc"),
            df_disk1=views.get("disk1"),
            df_disk2=views.get("disk2"),
            df_soh_events=df_soh_events,
            df_evt=df_evt,
        )

        res.update({
            "df_soh": df_soh,
            "df_soh_events": df_soh_events,
            "df_soh_msgs": df_soh_msgs,
            "views": views,
            "df_evt": df_evt,
            "tables": tables,
        })

    if verbose:
        print("== META ==")
        print("logfile      :", logfile)
        print("rt2ms_version :", meta.get("rt2ms_version"))
        print("run_time_utc  :", meta.get("run_time_utc"))
        print()

        print("== CONTAGENS ==")
        print("SH blocks     :", len(dados_raw.get("SH", [])))
        print("SOH snapshots :", len(soh))
        print("EH events     :", sum(len(v) for v in (dados_raw.get("EH", {}) or {}).values()))
        print("ET events     :", sum(len(v) for v in (dados_raw.get("ET", {}) or {}).values()))
        print()

        if soh:
            print("== SOH RANGE ==")
            print("first :", soh[0].get("time"))
            print("last  :", soh[-1].get("time"))
            print()

        print("== METRIC KEYS ==")
        print("n_metric_keys :", len(metric_keys))
        print("metric_keys   :", metric_keys)
        print()

        print("== FREQUÊNCIA (top) ==")
        for k, n in cnt.most_common(20):
            frac = (n / float(len(soh))) if len(soh) else 0.0
            print("  %-22s %6d  (%6.2f%%)" % (k, n, 100.0 * frac))
        print()

        print("== SUSPECTS ==")
        if suspects:
            print(sorted(suspects))
        else:
            print("(nenhum)")
        print()

        if make_frames:
            import pandas as pd
            print("== DF_SOH ==")
            print("shape   :", res["df_soh"].shape)
            print("columns :", list(res["df_soh"].columns))
            print()

            # histograma por hora do dia
            hh = _hour_hist_from_index(pd.DatetimeIndex(res["df_soh"].index))
            print("== SOH snapshots por hora do dia (0..23) ==")
            print(hh.to_string())
            print()

            # cobertura por views
            def _cov(df):
                return 0 if (df is None or len(df) == 0) else len(df)

            v = res["views"]
            print("== COBERTURA (linhas com pelo menos 1 valor) ==")
            for name in ("batt","mem","gps","bvtc","disk1","disk2"):
                dfv = v.get(name)
                if dfv is None or len(dfv) == 0:
                    print("%-8s : 0" % name)
                else:
                    print("%-8s : %d  range=[%s .. %s]" % (name, len(dfv), dfv.index.min(), dfv.index.max()))
            print()

            # eventos SOH por tipo
            df_e = res["df_soh_events"]
            if df_e is not None and len(df_e) and "type" in df_e.columns:
                print("== EVENTS (SOH) por tipo (top) ==")
                print(df_e["type"].value_counts().head(10).to_string())
                print()

            # top mensagens SOH
            df_m = res["df_soh_msgs"]
            if df_m is not None and len(df_m) and "msg" in df_m.columns:
                print("== TOP mensagens SOH ==")
                print(df_m["msg"].value_counts().head(15).to_string())
                print()

            # resumo external clock (duty)
            clk = res["tables"].get("external_clock_stats")
            if clk is not None and len(clk):
                print("== EXTERNAL CLOCK (estimativa ON/OFF por transições) ==")
                print(clk.to_string(index=False))
                print()

    return res


# -----------------------------------------------------------
# JSON export (opcional)
# -----------------------------------------------------------

class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, set):
            return sorted(o)
        return json.JSONEncoder.default(self, o)


def export_model_json(dados_model, out_path):
    ensure_dir(os.path.dirname(out_path))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dados_model, f, cls=_Encoder, ensure_ascii=False, indent=2)


# -----------------------------------------------------------
# CLI (opcional) — você pode ignorar e usar via IPython
# -----------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(description="RT130 rt2ms log → QC frames/tabelas (CSV/LaTeX).")
    ap.add_argument("logfile", help="Caminho do arquivo RT130_*.log")
    ap.add_argument("--out-dir", default=None, help="Diretório para export CSV/TEX")
    ap.add_argument("--prefix", default="rt130", help="Prefixo dos arquivos exportados")
    ap.add_argument("--no-frames", action="store_true", help="Não cria DataFrames (só parse/model)")
    ap.add_argument("--quiet", action="store_true", help="Não imprime resumo")
    ap.add_argument("--export-json-model", default=None, help="Salva dados_model em JSON (datetimes→ISO)")
    ap.add_argument("--export-csv", action="store_true", help="Exporta CSV dos frames/tabelas em out-dir")
    ap.add_argument("--export-tex", action="store_true", help="Exporta tabelas LaTeX (.tex) em out-dir")
    args = ap.parse_args()

    res = analyze_rt130_log(
        args.logfile,
        make_frames=(not args.no_frames),
        verbose=(not args.quiet),
    )

    if args.export_json_model:
        export_model_json(res["dados_model"], args.export_json_model)

    if args.out_dir and (args.export_csv or args.export_tex):
        ensure_dir(args.out_dir)

    if args.export_csv and args.out_dir and (not args.no_frames):
        frames = {
            "soh": res.get("df_soh"),
            "soh_events": res.get("df_soh_events"),
            "soh_msgs": res.get("df_soh_msgs"),
            "evt_eh_et": res.get("df_evt"),
        }
        # views
        for k, df in (res.get("views") or {}).items():
            frames["soh_%s" % k] = df
        # tables
        for k, df in (res.get("tables") or {}).items():
            frames["tbl_%s" % k] = df

        export_frames_csv(frames, args.out_dir, prefix=args.prefix)

    if args.export_tex and args.out_dir and (not args.no_frames):
        tables = res.get("tables") or {}
        for name, df in tables.items():
            out = os.path.join(args.out_dir, "%s_%s.tex" % (args.prefix, name))
            export_table_latex(df, out, caption=None, label=None, index=True, escape=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
