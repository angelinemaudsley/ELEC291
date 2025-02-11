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
# creates a CSV file and write the header for data logging
csv_filename = "data_log.csv"
import os
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])
# function to read serial data and yield time, temperature values
def data_gen():
    t = data_gen.t  # Initialize time counter
    while True:
        t += 1  # Increment time counter
        strin = ser.readline().decode('utf-8').strip()  # Read from serial, decode, and clean input
        cool = float(strin)  # Convert string input to float
        yield t, cool  # Yield time index and temperature value
# function to update the live graph with new data
def run(data):
    t, y = data  # unpacks time and temperature
    if t > -1:  #only processes valid time values
        xdata.append(t)  # stores time data
        ydata.append(y)  # variable for temperature data
        # adjusts the x-axis limits to keep data scrolling
        if t > xsize:
            ax.set_xlim(t - xsize, t)
        # adjusts the y-axis limits dynamically based on data range
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)
        # updates the plotted line with new data
        line.set_data(xdata, ydata)
        # compute real-time statistics
        mean_val = np.mean(ydata)  # compute mean temperatures - using numpy
        std_dev = np.std(ydata)    # Compute standard deviation - using numpy
        min_temp = min(ydata)      # find minimum recorded temperature - python func
        max_temp = max(ydata)      # Find maximum recorded temperature - python func
        avg_temp = sum(ydata) / len(ydata)  # Compute average temperature - python func
        # this updates update the text box with computed statistics
        text_box.set_text(
            f"Mean: {mean_val:.2f}\n"
            f"Std Dev: {std_dev:.2f}\n"
            f"Min: {min_temp:.2f}\n"
            f"Max: {max_temp:.2f}\n"
            f"Avg Temp: {avg_temp:.2f}"
        )
        # logging the data to the CSV file with timestamp - lowkey like a data logger
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current time
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, t, y, mean_val, std_dev, min_temp, max_temp, avg_temp])
    return line,  # Return the updated line object
# function to handle closing of the figure (ensures clean exit)
def on_close_figure(event):
    sys.exit(0)
# initialize time index for data generation
data_gen.t = -1
# create the figure and subplot for graphing
fig = plt.figure()
fig.canvas.mpl_connect('close_event', on_close_figure)  # close event handler
ax = fig.add_subplot(111)  # create a single subplot
line, = ax.plot([], [], lw=2)  # initialize an empty line
# set initial graph axis limits
ax.set_ylim(0, 100)  # initial temperature range (adjust dynamically)
ax.set_xlim(0, xsize)  # x-axis range for scrolling effect
ax.grid()  # add grid for better readability
# lists to store real-time data
xdata, ydata = [], []
# add a text box to display computed statistics in real-time
text_box = ax.text(0.7, 0.9, "", transform=ax.transAxes, fontsize=12,
                   bbox=dict(facecolor="white", alpha=0.5))
# create an animation function that continuously updates the graph
ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)
# display the graph
plt.show()
