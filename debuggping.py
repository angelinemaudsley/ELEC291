import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, time, math, threading
import serial
import pyttsx3
import csv
import speech_recognition as sr
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
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

# Global variable for latest temperature
latest_temperature = None

def data_gen():
    global latest_temperature
    t = data_gen.t  # Initialize time counter
    while True:
        t += 1  # Increment time counter
        strin = ser.readline().decode('utf-8').strip()  # Read from serial, decode, and clean input
        cool = float(strin)  # Convert string input to float
        latest_temperature = cool  # Store latest temperature for speech response
        yield t, cool  # Yield time index and temperature value

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

def on_close_figure(event):
    sys.exit(0)

def recognize_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    engine = pyttsx3.init()  # Initialize the text-to-speech engine

    global latest_temperature
    while True:
        with mic as source:
            print("Listening for voice command...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        try:
            command = recognizer.recognize_google(audio).lower()
            if "current temperature" in command:
                if latest_temperature is not None:
                    response = f"The current temperature is {latest_temperature:.2f} degrees Celsius"
                    print(response)
                    engine.say(response)  # Speak the response
                    engine.runAndWait()
                else:
                    print("Temperature data is not yet available.")
                    engine.say("Temperature data is not yet available.")
                    engine.runAndWait()
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except sr.RequestError:
            print("Speech recognition service unavailable.")

# Start speech recognition in a separate thread
speech_thread = threading.Thread(target=recognize_speech, daemon=True)
speech_thread.start()

# Initialize time index for data generation
data_gen.t = -1

# Create the figure and subplot for graphing
plt.style.use('dark_background')
fig = plt.figure(figsize=(10, 6))
fig.canvas.mpl_connect('close_event', on_close_figure)
ax = fig.add_subplot(111)

# Set futuristic styling
grid_color = '#444'
line_color = '#00ffcc'
text_color = '#ffffff'

ax.set_facecolor("#121212")
ax.grid(color=grid_color, linestyle='--', linewidth=0.5)
ax.spines['bottom'].set_color(text_color)
ax.spines['top'].set_color(text_color)
ax.spines['left'].set_color(text_color)
ax.spines['right'].set_color(text_color)
ax.xaxis.label.set_color(text_color)
ax.yaxis.label.set_color(text_color)
ax.tick_params(axis='x', colors=text_color)
ax.tick_params(axis='y', colors=text_color)

# Set axis labels
ax.set_xlabel("Time (s)", fontsize=12, color=text_color)
ax.set_ylabel("Temperature (°C)", fontsize=12, color=text_color)

line, = ax.plot([], [], lw=2, color=line_color)
ax.set_ylim(0, 100)
ax.set_xlim(0, xsize)

xdata, ydata = [], []

text_box = ax.text(
    1.05, 0.5, "", transform=ax.transAxes, fontsize=12, color=text_color,
    bbox=dict(facecolor="#333", alpha=0.7, edgecolor=line_color), verticalalignment='center'
)

ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)

plt.show()

