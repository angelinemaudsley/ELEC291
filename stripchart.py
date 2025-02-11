import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, os, time, math
import serial
import csv
import pygame
import speech_recognition as sr
import pyttsx3
from datetime import datetime
from matplotlib.table import Table

# Check if background.mp3 exists before loading
music_file = "background.mp3"
if not os.path.exists(music_file):
    print(f"Error: {music_file} not found!")
    sys.exit(1)  # Exit the program if music is missing

# Initialize pygame mixer for audio
pygame.mixer.init()
pygame.mixer.music.load(music_file)  # Load background music
pygame.mixer.music.play(-1)  # Loop music indefinitely

# Serial Port Configuration
ser = serial.Serial(
    port='COM8',  # Change this to your actual COM port
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS
)

xsize = 20  # Number of data points visible on the graph at a time

# Music Pitch Adjusts with Temperature
def set_music_pitch(temperature):
    min_temp, max_temp = 20, 50
    min_speed, max_speed = 0.8, 1.5

    norm_temp = (temperature - min_temp) / (max_temp - min_temp)
    norm_temp = max(0, min(norm_temp, 1))  # Keep in range 0-1

    pitch = min_speed + (max_speed - min_speed) * norm_temp

    pygame.mixer.quit()
    pygame.mixer.init(frequency=int(44100 * pitch))
    pygame.mixer.music.play(-1, fade_ms=500)

# Data Logging
csv_filename = "data_log.csv"
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

# Initialize Speech Engine
engine = pyttsx3.init()
recognizer = sr.Recognizer()

def speak(text):
    engine.say(text)
    engine.runAndWait()

latest_temp = None  # Store the latest temperature

#  Data Generator
def data_gen():
    global latest_temp
    t = data_gen.t
    while True:
        if not paused:
            t += 1
            strin = ser.readline().decode(errors="ignore").strip()
            
            try:
                cool = float(strin)
                latest_temp = cool
                set_music_pitch(cool)
                yield t, cool
            except ValueError:
                continue  # Skip invalid data

data_gen.t = -1  # Start time counter at -1

# Voice Command Handling
def listen_for_command():
    with sr.Microphone() as source:
        print("🎙️ Listening for command...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            command = recognizer.recognize_google(audio).lower()
            if "current temperature" in command:
                if latest_temp is not None:
                    speak(f"The current temperature is {latest_temp:.2f} degrees Celsius")
                else:
                    speak("Temperature data is not available yet.")
        except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError):
            print("⚠️ Could not process the audio.")

# Pause/Resume functionality
paused = False  

def on_key(event):
    global paused
    if event.key == 'p':
        paused = not paused
        print("⏸ Paused" if paused else "▶ Resumed")

# Initialize figure
plt.style.use('dark_background')
fig, ax = plt.subplots()
fig.canvas.mpl_connect('close_event', lambda event: (pygame.mixer.music.stop(), pygame.mixer.quit(), sys.exit(0)))
fig.canvas.mpl_connect("key_press_event", on_key)

# Dark Mode UI Styling
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

line, = ax.plot([], [], lw=2, color=line_color)
ax.set_ylim(0, 100)
ax.set_xlim(0, xsize)

xdata, ydata = [], []

# Text Box for Stats
text_box = ax.text(
    1.05, 0.5, "", transform=ax.transAxes, fontsize=12, color=text_color,
    bbox=dict(facecolor="#333", alpha=0.7, edgecolor=line_color), verticalalignment='center'
)

# Graph Update Function
def run(data):
    global latest_temp
    if paused:
        return line,  # Prevent updates if paused
    
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

        # Ensure `ydata` has enough values before calculating stats
        if len(ydata) > 1:
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

        # Listen for voice command
        listen_for_command()

    return line,

# Start Animation
ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=1000, repeat=False)
plt.show()

