#!/usr/bin/python
import csv
import time
from tkinter import *
import serial
import serial.tools.list_ports
import kconvert

top = Tk()
top.resizable(0, 0)
top.title("Fluke_45/Tek_DMM4020 K-type Thermocouple")

LOG_FILE = "temperature_log.csv"

CJTemp = StringVar()
Temp = StringVar()
DMMout = StringVar()
portstatus = StringVar()
DMM_Name = StringVar()
connected = 0
global ser

def log_data(timestamp, multimeter_temp):
    with open(LOG_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, multimeter_temp])

def update_temp():
    global ser, connected
    if connected == 0:
        top.after(5000, FindPort)
        return
    try:
        strin = ser.readline().rstrip().decode()
        ser.readline()
        if len(strin) > 1 and strin[1] == '>':
            strin = ser.readline()
        ser.write(b"MEAS1?\r\n")
    except:
        connected = 0
        DMMout.set("----")
        Temp.set("----")
        portstatus.set("Communication Lost")
        DMM_Name.set("--------")
        top.after(5000, FindPort)
        return
    
    strin_clean = strin.replace("VDC", "").strip()
    if strin_clean:
        try:
            val = float(strin_clean) * 1000.0
            cj = float(CJTemp.get()) if CJTemp.get() else 0.0
            ktemp = round(kconvert.mV_to_C(val, cj), 1)
            Temp.set(ktemp if -200 < ktemp < 1372 else "OUT")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_data(timestamp, ktemp)
        except:
            Temp.set("----")
    else:
        Temp.set("----")
        connected = 0
    top.after(500, update_temp)

def FindPort():
    global ser, connected
    try:
        ser.close()
    except:
        pass
    connected = 0
    portlist = list(serial.tools.list_ports.comports())
    for item in reversed(portlist):
        portstatus.set("Trying port " + item[0])
        top.update()
        try:
            ser = serial.Serial(item[0], 9600, timeout=0.5)
            ser.write(b"\x03")
            pstring = ser.readline().rstrip().decode()
            if len(pstring) > 1 and pstring[1] == '>':
                ser.timeout = 3
                portstatus.set("Connected to " + item[0])
                ser.write(b"VDC; RATE S; *IDN?\r\n")
                DMM_Name.set(ser.readline().rstrip().decode())
                ser.readline()
                ser.write(b"MEAS1?\r\n")
                connected = 1
                top.after(1000, update_temp)
                break
            else:
                ser.close()
        except:
            connected = 0
    if connected == 0:
        portstatus.set("Multimeter not found")
        top.after(5000, FindPort)

Label(top, text="Cold Junction Temperature:").grid(row=1, column=0)
Entry(top, bd=1, width=7, textvariable=CJTemp).grid(row=2, column=0)
Label(top, text="Multimeter reading:").grid(row=3, column=0)
Label(top, text="xxxx", textvariable=DMMout, width=20, font=("Helvetica", 20), fg="red").grid(row=4, column=0)
Label(top, text="Thermocouple Temperature (C)").grid(row=5, column=0)
Label(top, textvariable=Temp, width=5, font=("Helvetica", 100), fg="blue").grid(row=6, column=0)
Label(top, text="xxxx", textvariable=portstatus, width=40, font=("Helvetica", 12)).grid(row=7, column=0)
Label(top, text="xxxx", textvariable=DMM_Name, width=40, font=("Helvetica", 12)).grid(row=8, column=0)
Button(top, width=11, text="Exit", command=top.destroy).grid(row=9, column=0)

CJTemp.set("22")
DMMout.set("NO DATA")
DMM_Name.set("--------")

try:
    with open(LOG_FILE, "x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Multimeter Temp (C)"])
except FileExistsError:
    pass

top.after(500, FindPort)
top.mainloop()

