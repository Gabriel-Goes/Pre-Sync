#!/usr/bin/env python3
import re
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def process_battery_data(filename, year=2024):
    pattern = re.compile(
        r"(\d{3}):(\d{2}):(\d{2}):(\d{2})\s+BATTERY VOLTAGE = (\d+\.\d+)V,\s+TEMPERATURE = (-?\d+)C,\s+BACKUP = (\d+\.\d+)V"
    )
    data = []
    with open(filename, 'r', encoding='ISO-8859-1') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                day_of_year = int(match.group(1))
                time_str = str({match.group(2)}:{match.group(3)}:{match.group(4)}
                # Converte o dia do ano e o horário para timestamp
                timestamp = datetime.strptime(f"{year} {day_of_year} {time_str}", "%Y %j %H:%M:%S")
                battery_voltage = float(match.group(5))
                temperature = int(match.group(6))
                backup_voltage = float(match.group(7))
                data.append({
                    "timestamp": timestamp,
                    "battery_voltage": battery_voltage,
                    "temperature": temperature,
                    "backup_voltage": backup_voltage
                })
    if not data:
        raise ValueError("Nenhum dado encontrado no arquivo.")
    df = pd.DataFrame(data)
    df.sort_values("timestamp", inplace=True)
    return df


def plot_battery_data(df):
    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # Plot Tensão da Bateria
    axs[0].plot(df["timestamp"], df["battery_voltage"], marker='o', linestyle='-', label="Battery Voltage (V)")
    min_voltage = df["battery_voltage"].min()
    axs[0].axhline(y=min_voltage, color='r', linestyle='--', linewidth=0.5, label=f"Min Voltage: {min_voltage}V")
    axs[0].set_ylabel("Battery Voltage (V)")
    axs[0].set_title("Battery Voltage Over Time")
    axs[0].legend()
    axs[0].grid(True)

    # Plot Temperatura
    axs[1].plot(df["timestamp"], df["temperature"], marker='o', linestyle='-', color="orange", label="Temperature (°C)")
    min_temp = df["temperature"].min()
    axs[1].axhline(y=min_temp, color='r', linestyle='--', linewidth=0.5, label=f"Min Temp: {min_temp}°C")
    axs[1].set_ylabel("Temperature (°C)")
    axs[1].set_title("Temperature Over Time")
    axs[1].legend()
    axs[1].grid(True)

    # Plot Tensão de Backup
    axs[2].plot(df["timestamp"], df["backup_voltage"], marker='o', linestyle='-', color="green", label="Backup Voltage (V)")
    axs[2].set_ylabel("Backup Voltage (V)")
    axs[2].set_xlabel("Timestamp")
    axs[2].set_title("Backup Voltage Over Time")
    axs[2].legend()
    axs[2].grid(True)

    plt.xticks(rotation=45)
    plt.tight_layout()
    # plt.show()
    plt.savefig("battery_data_plot.png", dpi=300)


def main():
    parser = argparse.ArgumentParser(description="Plot Battery Data")
    parser.add_argument("filename", help="Caminho para o arquivo de dados de bateria")
    parser.add_argument("--year", type=int, default=2024, help="Ano dos dados (padrão: 2024)")
    args = parser.parse_args()

    try:
        df = process_battery_data(args.filename, year=args.year)
    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")
        sys.exit(1)

    plot_battery_data(df)


if __name__ == "__main__":
    main()
