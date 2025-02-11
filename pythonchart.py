import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button, RadioButtons, CheckButtons
import sys, time, math
import serial
import csv
import os
import speech_recognition as sr
import pyttsx3
from datetime import datetime

# Configure the serial port for data input
ser = serial.Serial(
    port='COM8',  # set to the correct COM port
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_TWO,
    bytesize=serial.EIGHTBITS
)

# Initialize speech engine
engine = pyttsx3.init()
recognizer = sr.Recognizer()

def speak(text):
    engine.say(text)
    engine.runAndWait()

xsize = 20  # Number of data points visible on the graph at a time

csv_filename = "data_log.csv"
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

latest_temp = None  # Variable to store latest temperature

def data_gen():
    global latest_temp
    t = data_gen.t  # Initialize time counter
    while True:
        t += 1  # Increment time counter
        strin = ser.readline().decode('utf-8').strip()  # Read from serial, decode, and clean input
        cool = float(strin)  # Convert string input to float
        latest_temp = cool  # Store latest temperature value
        yield t, cool  # Yield time index and temperature value

def listen_for_command():
    with sr.Microphone() as source:
        print("Listening for command...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            command = recognizer.recognize_google(audio).lower()
            if "current temperature" in command:
                if latest_temp is not None:
                    speak(f"The current temperature is {latest_temp:.2f} degrees Celsius")
                else:
                    speak("Temperature data is not available yet.")
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError:
            print("Speech recognition service is unavailable.")
        except sr.WaitTimeoutError:
            print("Listening timed out.")


def run(data):
    global latest_temp
    t, y = data  # Unpack time and temperature
    if t > -1:
        xdata.append(t)
        ydata.append(y)
        
        if t > xsize:
            ax.set_xlim(t - xsize, t)
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)
        
        line.set_data(xdata, ydata)
        
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
        
        listen_for_command()
    
    return line,

def on_close_figure(event):
    sys.exit(0)

data_gen.t = -1

plt.style.use('dark_background')
fig = plt.figure(figsize=(10, 6))
fig.canvas.mpl_connect('close_event', on_close_figure)
ax = fig.add_subplot(111)

grid_color = '#444'
line_color = 'cyan'
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

line, = ax.plot([], [], lw=2, color=line_color)
ax.set_ylim(0, 100)
ax.set_xlim(0, xsize)

xdata, ydata = [], []

text_box = ax.text(
    1.05, 0.5, "", transform=ax.transAxes, fontsize=12, color=text_color,
    bbox=dict(facecolor="#333", alpha=0.7, edgecolor=line_color), verticalalignment='center'
)

ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)

# button that allows us to change the line colour
axcolor = 'darkcyan'
rax = plt.axes([0.05, 0.4, 0.15, 0.15], facecolor=axcolor)

radio = RadioButtons(rax, ['cyan', 'red', 'lime'], activecolor='m')

def color(labels):
    line.set_color(labels)  # Change line color dynamically
    fig.canvas.draw()
radio.on_clicked(color)

# Display the graph
plt.show()


