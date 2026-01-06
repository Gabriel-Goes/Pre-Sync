import sys
import re
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

def dms_to_decimal(dms):
    """
    Converte uma coordenada no formato DMS (ex.: "N23:21:47.24" ou "W045:38:41.80")
    para o formato decimal.
    """
    direction = dms[0]
    parts = dms[1:].split(':')
    deg, minutes, seconds = map(float, parts)
    decimal = deg + minutes / 60 + seconds / 3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

def parse_line(line):
    """
    Extrai o timestamp e as coordenadas de uma linha que tenha o padrão:
      084:16:00:00 GPS: POSITION: S23:21:47.24 W045:38:41.80 +00779M
    """
    pattern = r'(\d{3}:\d{2}:\d{2}:\d{2}).*?([NS]\d{2}:\d{2}:\d{2}\.\d+)\s+([EW]\d{3}:\d{2}:\d{2}\.\d+)'
    m = re.search(pattern, line)
    if m:
        ts_str, lat_str, lon_str = m.groups()
        day_julian, hour, minute, second = map(int, ts_str.split(':'))
        timestamp = datetime(2025, 1, 1) + timedelta(days=day_julian - 1,
                                                     hours=hour,
                                                     minutes=minute,
                                                     seconds=second)
        latitude = dms_to_decimal(lat_str)
        longitude = dms_to_decimal(lon_str)
        return timestamp, latitude, longitude
    return None

def main():
    if len(sys.argv) != 2:
        print("Uso: python gps_boxplot.py <arquivo.gps>")
        sys.exit(1)

    filename = sys.argv[1]
    data = []

    with open(filename, "r", encoding="latin1") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                data.append(parsed)

    if not data:
        print("Nenhum dado válido encontrado no arquivo.")
        sys.exit(1)



    df = pd.DataFrame(data, columns=["timestamp", "latitude", "longitude"])
    df.set_index("timestamp", inplace=True)


    # —– Parte que gera os boxplots em subplots separados —–

    # Cria uma figura com 1 linha e 2 colunas
    fig, (ax_lat, ax_lon) = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))

    # Boxplot de latitude no primeiro subplot
    ax_lat.boxplot(df["latitude"].dropna())
    ax_lat.set_title("Latitude")
    ax_lat.set_ylabel("Graus Decimais")
    ax_lat.grid(True, axis='y')

    # Boxplot de longitude no segundo subplot
    ax_lon.boxplot(df["longitude"].dropna())
    ax_lon.set_title("Longitude")
    ax_lon.set_ylabel("Graus Decimais")
    ax_lon.grid(True, axis='y')

    # Ajusta layout e salva
    plt.tight_layout()
    plt.savefig("gps_boxplot_separados.png")
    print("Boxplots salvos como 'gps_boxplot_separados.png'.")

if __name__ == "__main__":
    main()
