import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, time, math
import serial
import csv
import os
import speech_recognition as sr
import pyttsx3
from datetime import datetime
import pygame

# Serial Port Configuration
ser = serial.Serial(
    port='COM8',  # Change this to your actual COM port
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS
)

# Initialize pygame mixer for audio
music_file = r"C:\Users\chand\background.mp3"
pygame.mixer.init()
pygame.mixer.music.load(music_file)  # Load background music
pygame.mixer.music.play(-1)  # Loop music indefinitely

def set_music_pitch(temperature):
    min_temp, max_temp = 20, 50
    min_speed, max_speed = 0.8, 1.5

    norm_temp = (temperature - min_temp) / (max_temp - min_temp)
    norm_temp = max(0, min(norm_temp, 1))  # Keep in range 0-1

    pitch = min_speed + (max_speed - min_speed) * norm_temp

    pygame.mixer.quit()
    pygame.mixer.init(frequency=int(44100 * pitch))
    pygame.mixer.music.play(-1, fade_ms=500)

# Initialize Speech Engine
engine = pyttsx3.init()
recognizer = sr.Recognizer()

def speak(text):
    engine.say(text)
    engine.runAndWait()

xsize= 20

# Data Logging
csv_filename = "data_log.csv"
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

latest_temp = None  # Store the latest temperature

#  Data Generator
def data_gen():
    global latest_temp
    t = data_gen.t
    while True:
        if not paused:
            t += 1
            strin = ser.readline().decode('utf-8').strip()
            try:
                cool = float(strin)
                latest_temp = cool
                set_music_pitch(cool)
                yield t, cool
            except ValueError:
                continue  # Skip invalid data

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
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError:
            print("Speech recognition service is unavailable.")
        except sr.WaitTimeoutError:
            print("Listening timed out.")

# Pause/Resume functionality
paused = False  
def on_key(event):
    global paused
    if event.key == 'p':
        paused = not paused
        print(" Paused" if paused else " Resumed")

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

text_box = ax.text(
    1.05, 0.5, "", transform=ax.transAxes, fontsize=12, color=text_color,
    bbox=dict(facecolor="#333", alpha=0.7, edgecolor=line_color), verticalalignment='center'
)

ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)
plt.show()

