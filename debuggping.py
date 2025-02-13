import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import RadioButtons
import sys, time, math, threading
import serial
import pyttsx3
import csv
import speech_recognition as sr
from datetime import datetime
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pygame
import os

# configuring the serial port for data input
ser = serial.Serial(
    port='COM13',  # set to the correct COM port
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_TWO,
    bytesize=serial.EIGHTBITS
)

xsize = 20  # this is the nuumber of data points visible on the graph at a time, changed to 20 to see more.
csv_filename = "data_log.csv"

print(f"CSV is saved at: {os.path.abspath(csv_filename)}") #this shows were csv file is saved for debugging.

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"]) #headers for csv file

latest_temperature = None

def data_gen():
    global paused
    global latest_temperature
    t = data_gen.t  
    while True:
        if paused:
            yield t, ydata[-1] if ydata else 0  # Keep yielding last known temperature
            continue
        
        t += 1  
        try:
            strin = ser.readline().decode('utf-8').strip()  
            cool = float(strin)  
            latest_temperature = cool  
            yield t, cool  
        except ValueError:
            print("Invalid temperature data received.")

def run(data):
    global latest_temperature
    if paused:
        return line,  # Stops graph updates

    t, y = data  
    if t > -1:  
        xdata.append(t)  
        ydata.append(y)  

        ax.set_xlim(0, t)  # Scale x-axis from 0 to latest time
        ax.set_ylim(min(ydata) - 5, max(ydata) + 5)  # Dynamically scale y-axis

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
        
    return line,    
  
# email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "elaminbrown@gmail.com"  
EMAIL_PASSWORD = "xmcq ggpl dpmi evtx"  
TO_EMAIL = "elaminbrown@gmail.com"  #change this if you want

def send_email_with_csv():
    subject = "Reflow Oven Data Log"
    body = "Attached is the temperature log from the reflow oven session."

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with open(csv_filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(csv_filename)}")
            msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, TO_EMAIL, msg.as_string())
        server.quit()

        print(f"Email with CSV sent to {TO_EMAIL}")

    except Exception as e:
        print(f"Error sending email: {e}")

#sends email when closes figure.
def on_close_figure(event):
    print("Reflow process complete. Sending data log email...")
    send_email_with_csv()
    sys.exit(0)

#recognizes speech to give current temp.
def recognize_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    engine = pyttsx3.init()  

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
                    engine.say(response)  
                    engine.runAndWait()
                else:
                    print("Temperature data is not yet available.")
                    engine.say("Temperature data is not yet available.")
                    engine.runAndWait()
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except sr.RequestError:
            print("Speech recognition service unavailable.")

speech_thread = threading.Thread(target=recognize_speech, daemon=True)
speech_thread.start()

# Pause/Resume functionality
paused = False  
def on_key(event):
    global paused
    if event.key == 'p':
        paused = not paused
        if paused:
            print("Paused")
        else:
            print("Resumed")

data_gen.t = -1
#aestheically pleasing stuff
plt.style.use('dark_background')
fig = plt.figure(figsize=(10, 6))
fig.canvas.mpl_connect('key_press_event', on_key)
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

#changes colour of line with button
axcolor = 'darkcyan'
ax_pos = ax.get_position().bounds  # (left, bottom, width, height)

# Define rax position relative to ax
rax_left = ax_pos[0] + 0.3 * ax_pos[2]  # Center the buttons under the graph
rax_bottom = ax_pos[1] - 0.12  # Place below the graph
rax_width = 0.4 * ax_pos[2]  # middle of graph
rax_height = 0.08 

rax = plt.axes([rax_left, rax_bottom, rax_width, rax_height], facecolor=axcolor)
radio = RadioButtons(rax, ['cyan', 'red', 'lime'], activecolor='m')

def color(labels):
    line.set_color(labels)  
    fig.canvas.draw()
radio.on_clicked(color)

plt.show()
