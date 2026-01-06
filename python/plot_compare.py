#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from obspy.clients.filesystem.sds import Client
from obspy.core import UTCDateTime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def parse_args():
    p = argparse.ArgumentParser(
        description="Compara gaps entre duas SDS usando ObsPy e plota Gantt."
    )
    p.add_argument(
        "--local", "-L",
        default="/home/suporte/TMP/SYNC/PRB1_20250703/sds/",
        help="Caminho para SDS local (default: %(default)s)"
    )
    p.add_argument(
        "--ref", "-R",
        default="/SDS/",
        help="Caminho para SDS de referência (default: %(default)s)"
    )
    p.add_argument(
        "--start", "-S", required=True,
        help="Data de início no formato YYYY-MM-DD"
    )
    p.add_argument(
        "--end", "-E", required=True,
        help="Data final no formato YYYY-MM-DD"
    )
    p.add_argument(
        "--network", "-N", default="BL",
        help="Código de rede (default: %(default)s)"
    )
    p.add_argument(
        "--station", "-T", default="PRB1",
        help="Código de estação (default: %(default)s)"
    )
    p.add_argument(
        "--location", "-LCT", default="",
        help="Código de localização, use '' se vazio (default: %(default)s)"
    )
    p.add_argument(
        "--channel", "-C", default="HHZ",
        help="Código de canal (default: %(default)s)"
    )
    return p.parse_args()

def to_datetime(utc):
    # UTCDateTime → datetime.datetime
    return utc.datetime

def main():
    args = parse_args()

    # Parse interval
    t0 = UTCDateTime(args.start + "T00:00:00")
    t1 = UTCDateTime(args.end + "T23:59:59")

    # Initialize clients
    c_local = Client(args.local)
    c_ref   = Client(args.ref)

    # Load and sort streams
    st_local = c_local.get_waveforms(
        args.network, args.station, args.location, args.channel, t0, t1
    )
    st_ref   = c_ref.get_waveforms(
        args.network, args.station, args.location, args.channel, t0, t1
    )
    st_local.sort(keys=["starttime"])
    st_ref.sort(keys=["starttime"])

    # Extract gaps: tuples (net,sta,loc,cha,start,end,duration,n_missing)
    gaps_local = st_local.get_gaps()
    gaps_ref   = st_ref.get_gaps()

    # Plot Gantt
    fig, ax = plt.subplots(figsize=(12, 2))
    y_positions = [(gaps_local, 1.5, "red",    "Local SDS"),
                   (gaps_ref,   0.5, "orange","/SDS Ref")]

    for gaps, y, color, label in y_positions:
        first = True
        for gap in gaps:
            start = to_datetime(gap[4])
            end   = to_datetime(gap[5])
            ax.broken_barh(
                [(mdates.date2num(start), mdates.date2num(end) - mdates.date2num(start))],
                (y, 0.8),
                facecolors=color,
                label=label if first else ""
            )
            first = False

    # Formatting
    ax.set_ylim(0, 3)
    ax.set_yticks([1, 2])
    ax.set_yticklabels(["/SDS Ref", "Local SDS"])
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    title = f"Gaps {args.start} → {args.end} | {args.network}.{args.station}.{args.location}.{args.channel}"
    ax.set_title(title)
    ax.grid(True)

    # Legend without duplicates
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

