import numpy as np  
import matplotlib.pyplot as plt 
import matplotlib.animation as animation 
import seaborn as sns
import sys, time, math, os
import serial
import csv
from datetime import datetime

# Configure the serial port for data input
try:
    ser = serial.Serial(
        port='COM8',               # Adjust for your system
        baudrate=115200,           
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_TWO, 
        bytesize=serial.EIGHTBITS, 
        timeout=1  # Prevent blocking indefinitely
    )
except serial.SerialException as e:
    print(f"Serial error: {e}")
    sys.exit(1)

xsize = 20  # Number of data points visible on the graph at a time

# Create a CSV file and write the header if it does not exist
csv_filename = "data_log.csv"
csv_exists = os.path.isfile(csv_filename)

print(f"CSV is saved at: {os.path.abspath(csv_filename)}")

with open(csv_filename, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not csv_exists:
        writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

# Function to read serial data and yield time, temperature values
def data_gen():
    data_gen.t = 0  # Initialize time counter
    while True:
        try:
            strin = ser.readline().decode('utf-8').strip()  # Read from serial
            if not strin:  
                continue  # Skip empty reads
            
            cool = float(strin)  # Convert string input to float
            data_gen.t += 1
            yield data_gen.t, cool  # Yield time index and temperature value
        
        except ValueError:
            print("Invalid data received, skipping...")
            continue  # Skip invalid readings

# Function to update the live graph with new data
def run(data):
    t, y = data  # Unpacks time and temperature
    xdata.append(t)  # Append new data points
    ydata.append(y)

    # Keep only the last `xsize` data points to limit memory usage
    if len(xdata) > xsize:
        xdata.pop(0)
        ydata.pop(0)

    # Adjusts the x-axis limits dynamically
    ax.set_xlim(max(0, t - xsize), t)
    
    # Dynamically adjust y-axis based on data range with buffer
    y_min, y_max = min(ydata), max(ydata)
    ax.set_ylim(y_min - 5, y_max + 5)

    # Update the plotted line with new data
    line.set_data(xdata, ydata)

    # Compute real-time statistics
    mean_val = np.mean(ydata)
    std_dev = np.std(ydata)
    min_temp = y_min
    max_temp = y_max
    avg_temp = sum(ydata) / len(ydata)

    # Remove previous text annotations before adding new ones
    for txt in ax.texts:
        txt.remove()

    # Add updated statistics text dynamically to the right of the graph
    stats_text = (
        f"Mean: {mean_val:.2f}°C\n"
        f"Std Dev: {std_dev:.2f}\n"
        f"Min: {min_temp:.2f}°C\n"
        f"Max: {max_temp:.2f}°C\n"
        f"Avg Temp: {avg_temp:.2f}°C"
    )
    ax.text(t + 1, (y_min + y_max) / 2, stats_text, fontsize=12, color='white', 
            verticalalignment='center', bbox=dict(facecolor='black', alpha=0.5, edgecolor='white'))

    fig.canvas.draw_idle()  # Redraw the figure

    # Logging the data to the CSV file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, t, y, mean_val, std_dev, min_temp, max_temp, avg_temp])

    return line,  # Return the updated line object


