import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, time, math
import serial
import csv
from datetime import datetime

# Configure the serial port for data input
ser = serial.Serial(
    port='COM8',               # set to the correct COM port
    baudrate=115200,           
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_TWO, 
    bytesize=serial.EIGHTBITS 
)

xsize = 20  # Number of data points visible on the graph at a time

# Bonus Feature: Data Logging
csv_filename = "data_log.csv"
import os
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

def data_gen():
    t = data_gen.t  # Initialize time counter
    while True:
        t += 1
        strin = ser.readline().decode('utf-8').strip()
        cool = float(strin)
        yield t, cool

def run(data):
    t, y = data
    if t > -1:
        xdata.append(t)
        ydata.append(y)

        if t > xsize:
            ax.set_xlim(t - xsize, t)
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)
        
        # Dynamic color change based on temperature
        color = plt.cm.coolwarm((y - min(ydata)) / (max(ydata) - min(ydata) + 1e-6))
        line.set_data(xdata, ydata)
        line.set_color(color)

        mean_val = np.mean(ydata)
        std_dev = np.std(ydata)
        min_temp = min(ydata)
        max_temp = max(ydata)
        avg_temp = sum(ydata) / len(ydata)
        
        text_box.set_text(
            f"Mean: {mean_val:.2f}\n"
            f"Std Dev: {std_dev:.2f}\n"
            f"Min: {min_temp:.2f}\n"
            f"Max: {max_temp:.2f}\n"
            f"Avg Temp: {avg_temp:.2f}"
        )
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, t, y, mean_val, std_dev, min_temp, max_temp, avg_temp])
    return line,

def on_close_figure(event):
    sys.exit(0)

data_gen.t = -1

plt.style.use('dark_background')  # Dark theme for better contrast
fig, ax = plt.subplots()
fig.canvas.mpl_connect('close_event', on_close_figure)

ax.set_facecolor('#121212')  # Dark background for better contrast
ax.grid(color='#555555')  # Subtle grid
line, = ax.plot([], [], lw=3, alpha=0.8)
ax.set_ylim(0, 100)
ax.set_xlim(0, xsize)
ax.set_xlabel("Time (s)", fontsize=12, color='white')
ax.set_ylabel("Temperature (°C)", fontsize=12, color='white')
ax.tick_params(axis='both', colors='white')

xdata, ydata = [], []
text_box = ax.text(0.7, 0.9, "", transform=ax.transAxes, fontsize=14,
                   bbox=dict(facecolor="white", alpha=0.5, edgecolor='black', boxstyle='round,pad=0.5'))

ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)
plt.show()
