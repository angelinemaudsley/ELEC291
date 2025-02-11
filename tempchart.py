import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, time, math
import serial
import csv
from datetime import datetime

# Configure the serial port for data input
ser = serial.Serial(
    port='COM8',  # set to the correct COM port
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_TWO,
    bytesize=serial.EIGHTBITS
)

xsize = 20  # Number of data points visible on the graph at a time

# Create a CSV file and write the header for data logging
csv_filename = "data_log.csv"
import os
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (Â°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

# Function to read serial data and yield time, temperature values
def data_gen():
    t = data_gen.t  # Initialize time counter
    while True:
        t += 1  # Increment time counter
        strin = ser.readline().decode('utf-8').strip()  # Read from serial, decode, and clean input
        cool = float(strin)  # Convert string input to float
        yield t, cool  # Yield time index and temperature value

# Function to update the live graph with new data
def run(data):
    t, y = data  # Unpack time and temperature
    if t > -1:  # Only processes valid time values
        xdata.append(t)  # Store time data
        ydata.append(y)  # Store temperature data

        # Adjust the x-axis limits to keep data scrolling
        if t > xsize:
            ax.set_xlim(t - xsize, t)
        
        # Adjust the y-axis limits dynamically based on data range
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)
        
        # Update the plotted line with new data
        line.set_data(xdata, ydata)
        
        # Compute real-time statistics
        mean_val = np.mean(ydata)
        std_dev = np.std(ydata)
        min_temp = min(ydata)
        max_temp = max(ydata)
        avg_temp = sum(ydata) / len(ydata)
        
        # Update the text box with computed statistics
        text_box.set_text(
            f"Mean: {mean_val:.2f}\n"
            f"Std Dev: {std_dev:.2f}\n"
            f"Min: {min_temp:.2f}\n"
            f"Max: {max_temp:.2f}\n"
            f"Avg Temp: {avg_temp:.2f}"
        )
        
        # Logging the data to the CSV file with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, t, y, mean_val, std_dev, min_temp, max_temp, avg_temp])
        
    return line,  # Return the updated line object

# Function to handle closing of the figure (ensures clean exit)
def on_close_figure(event):
    sys.exit(0)

# Initialize time index for data generation
data_gen.t = -1

# Create the figure and subplot for graphing
plt.style.use('dark_background')  # Set dark mode theme
fig = plt.figure(figsize=(10, 6))
fig.canvas.mpl_connect('close_event', on_close_figure)  # Close event handler
ax = fig.add_subplot(111)

# Set futuristic styling
grid_color = '#444'  # Dark grid lines
line_color = '#00ffcc'  # Neon cyan line color
text_color = '#ffffff'  # White text for readability

ax.set_facecolor("#121212")  # Dark background
ax.grid(color=grid_color, linestyle='--', linewidth=0.5)
ax.spines['bottom'].set_color(text_color)
ax.spines['top'].set_color(text_color)
ax.spines['left'].set_color(text_color)
ax.spines['right'].set_color(text_color)
ax.xaxis.label.set_color(text_color)
ax.yaxis.label.set_color(text_color)
ax.tick_params(axis='x', colors=text_color)
ax.tick_params(axis='y', colors=text_color)

line, = ax.plot([], [], lw=2, color=line_color)  # Initialize an empty line with neon color

# Set initial graph axis limits
ax.set_ylim(0, 100)  # Initial temperature range (adjust dynamically)
ax.set_xlim(0, xsize)  # X-axis range for scrolling effect

# Lists to store real-time data
xdata, ydata = [], []

# Add a text box to display computed statistics in real-time (moved to the right)
text_box = ax.text(
    1.05, 0.5, "", transform=ax.transAxes, fontsize=12, color=text_color,
    bbox=dict(facecolor="#333", alpha=0.7, edgecolor=line_color), verticalalignment='center'
)

# Create an animation function that continuously updates the graph
ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)

# Display the graph
plt.show()