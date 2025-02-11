import numpy as np  
import matplotlib.pyplot as plt 
import matplotlib.animation as animation 
import seaborn as sns
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

# Creates a CSV file and write the header for data logging
csv_filename = "data_log.csv"
import os
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

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
    t, y = data  # Unpacks time and temperature
    if t > -1:  # Only processes valid time values
        xdata.append(t)  # Stores time data
        ydata.append(y)  # Variable for temperature data
        
        # Adjusts the x-axis limits to keep data scrolling
        if t > xsize:
            ax.set_xlim(t - xsize, t)
        
        # Adjusts the y-axis limits dynamically based on data range with buffer
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)
        
        # Updates the plotted line with new data
        line.set_data(xdata, ydata)
        
        # Compute real-time statistics
        mean_val = np.mean(ydata)
        std_dev = np.std(ydata)
        min_temp = min(ydata)
        max_temp = max(ydata)
        avg_temp = sum(ydata) / len(ydata)
        
        # Clear and update the stats table
        stats_table.clear()
        stats_table.axis('off')
        table_data = [["Mean", f"{mean_val:.2f}"],
                      ["Std Dev", f"{std_dev:.2f}"],
                      ["Min", f"{min_temp:.2f}"],
                      ["Max", f"{max_temp:.2f}"],
                      ["Avg Temp", f"{avg_temp:.2f}"]]
        stats_table.table(cellText=table_data, colLabels=["Statistic", "Value"], loc='center', cellLoc='center', bbox=[0, 0, 1, 1])
        fig.canvas.draw_idle()  # Redraw the figure
        
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

# Apply dark mode style
plt.style.use('dark_background')

# Create the figure and subplot for graphing
fig, (ax, stats_table) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={'width_ratios': [2, 1]})
fig.canvas.mpl_connect('close_event', on_close_figure)  # Close event handler

# Initialize an empty line with better aesthetics
line, = ax.plot([], [], lw=2, color='deepskyblue', marker='o', markersize=5, linestyle='-')

# Set initial graph axis limits
ax.set_ylim(0, 100)  # Initial temperature range (adjust dynamically)
ax.set_xlim(0, xsize)  # x-axis range for scrolling effect
ax.grid(True, linestyle='--', alpha=0.6, color='gray')  # Add a subtle grid

# Labels and title
ax.set_title("Real-Time Temperature Monitoring", fontsize=14, fontweight='bold', color='white')
ax.set_xlabel("Time (s)", fontsize=12, color='white')
ax.set_ylabel("Temperature (°C)", fontsize=12, color='white')
ax.tick_params(axis='both', colors='white')

# Lists to store real-time data
xdata, ydata = [], []

# Create an empty table
stats_table.axis('off')

# Create an animation function that continuously updates the graph
ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)

# Display the graph
plt.show()
