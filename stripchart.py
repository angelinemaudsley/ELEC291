import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys, os, time, math
import serial
import csv
import pygame
from datetime import datetime
from matplotlib.table import Table

#for music

music_file = "background.mp3"
if not os.path.exists(music_file):
    print(f" Error: {music_file} not found!")
    sys.exit(1)  # Exit the program if music is missing

pygame.mixer.init()
pygame.mixer.music.load(music_file)  # Load music file, CHANGE IT
pygame.mixer.music.play(-1)  # Loop music indefinitely

# Configure the serial port for data input
ser = serial.Serial(
    port='COM8',               # set to the correct COM port
    baudrate=115200,           
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_TWO, 
    bytesize=serial.EIGHTBITS 
)
xsize = 20  # Number of data points visible on the graph at a time

#Bonus feature: music pitch adjustment with temperature
def set_music_pitch(temperature):
    min_temp, max_temp = 20, 50  # Define reasonable temp range
    min_speed, max_speed = 0.8, 1.5  # Min and max pitch speed

    norm_temp = (temperature - min_temp) / (max_temp - min_temp)
    norm_temp = max(0, min(norm_temp, 1))  # Keep in range 0-1

    # Scale the speed accordingly
    pitch = min_speed + (max_speed - min_speed) * norm_temp

    # Apply pitch shift
    pygame.mixer.quit()  # Reset mixer (needed for pitch changes)
    pygame.mixer.init(frequency=int(44100 * pitch))  # Adjust pitch
    pygame.mixer.music.play(-1, fade_ms=500)


# Bonus Feature: Data Logging
csv_filename = "data_log.csv"
print(f"CSV is saved at: {os.path.abspath(csv_filename)}")
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Time (s)", "Temperature (°C)", "Mean", "Std Dev", "Min", "Max", "Avg Temp"])

#BONUS: pause flag
paused = False

#data generator
def data_gen():
    t = data_gen.t  # Initialize time counter
    while True:
        if not paused:
            t += 1
            strin = ser.readline().decode('utf-8').strip()
            try:
                cool = float(strin)
                set_music_pitch(cool)
                yield t, cool
            except ValueError:
                continue

data_gen.t = -1

# Bonus: Pause/Resume functionality
def on_key(event):
    global paused
    if event.key == 'p':
        paused = not paused
        print("Paused" if paused else "Resumed")

#Bonus: FANCY FIGURE
plt.style.use('dark_background')  # Dark theme for better contrast
fig, ax = plt.subplots()
fig.canvas.mpl_connect('close_event', lambda event: (pygame.mixer.music.stop(), pygame.mixer.quit(), sys.exit(0)))
fig.canvas.mpl_connect("key_press_event", on_key)

ax.set_facecolor('#121212')  # Dark background for better contrast
ax.grid(color='#555555')  # Subtle grid
line, = ax.plot([], [], lw=3, alpha=0.8)

ax.set_ylim(0, 100)
ax.set_xlim(0, xsize)
ax.set_xlabel("Time (s)", fontsize=12, color='white')
ax.set_ylabel("Temperature (°C)", fontsize=12, color='white')
ax.tick_params(axis='both', colors='white')

xdata, ydata = [], []

#text box for stats
text_box = ax.text(0.7, 0.9, "", transform=ax.transAxes, fontsize=14,
                   bbox=dict(facecolor="white", alpha=0.5, edgecolor='black', boxstyle='round,pad=0.5'))
table = None

# Add this inside the run() function, after calculating the statistics
def update_table(mean_val, std_dev, min_temp, max_temp, avg_temp):
    global table
    cell_text = [[f"{mean_val:.2f}", f"{std_dev:.2f}", f"{min_temp:.2f}", f"{max_temp:.2f}", f"{avg_temp:.2f}"]]
    
    # Remove old table if it exists
    for artist in ax.get_children():
        if isinstance(artist, Table):
            artist.remove()
    
    table = ax.table(cellText=cell_text, colLabels=["Mean", "Std Dev", "Min", "Max", "Avg Temp"],
                     cellLoc='center', loc='bottom', bbox=[0, -0.3, 1, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(10)

#to update graph
def run(data):
    if paused:
        return line,
        
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

        if len(ydata)>1:
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
    
            # Update statistics table
            update_table(mean_val, std_dev, min_temp, max_temp, avg_temp)
    
            #log to csv
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, t, y, mean_val, std_dev, min_temp, max_temp, avg_temp])
    return line,

ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)
plt.show()

