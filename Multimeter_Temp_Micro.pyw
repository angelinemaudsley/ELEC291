#!/usr/bin/python
import sys
import time
import csv
import serial
import serial.tools.list_ports
import kconvert

if sys.version_info[0] < 3:
    import Tkinter
    from tkinter import *
    import tkMessageBox
else:
    import tkinter as Tkinter
    from tkinter import *
    from tkinter import messagebox as tkMessageBox


top = Tk()
top.resizable(0, 0)
top.title("Fluke_45/Tek_DMM40xx K-type Thermocouple")

# ATTENTION: Make sure the multimeter is configured at 9600 baud, 8-bits, parity none, 1 stop bit, echo Off
LOG_FILE = "sample.csv"

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

def Just_Exit():
    top.destroy()
    try:
        ser.close()
    except:
        pass

def update_temp():
    global ser, connected
    if connected == 0:
        top.after(5000, FindPort)  # Not connected, try to reconnect again in 5 seconds
        return
    try:
        strin_bytes = ser.readline()
        strin = strin_bytes.decode()
        ser.readline()
        if len(strin) > 1 and strin[1] == '>':
            strin_bytes = ser.readline()
            strin = strin_bytes.decode()
        ser.write(b"MEAS1?\r\n")
    except:
        connected = 0
        DMMout.set("----")
        Temp.set("----")
        portstatus.set("Communication Lost")
        DMM_Name.set("--------")
        top.after(5000, FindPort)
        return
    
    strin_clean = strin.replace("VDC", "")
    if len(strin_clean) > 0:
        DMMout.set(strin.replace("\r", "").replace("\n", ""))
        try:
            val = float(strin_clean) * 1000.0  # Convert from volts to millivolts
            valid_val = 1
        except:
            valid_val = 0

        try:
            cj = float(CJTemp.get())
        except:
            cj = 0.0

        strin2 = ser2.readline().rstrip().decode()
        val2 = float(strin2) if len(strin2) > 0 else 0
        
        if valid_val == 1:
            ktemp = round(kconvert.mV_to_C(val, cj), 1)
            if ktemp < -200:
                Temp.set("UNDER")
            elif ktemp > 1372:
                Temp.set("OVER")
            else:
                Temp.set(ktemp)
                try:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_data(timestamp, ktemp)  # Log the data
                    print(ktemp, val2, round(abs(ktemp - val2), 2))
                except:
                    pass
        else:
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
    DMM_Name.set("--------")
    portlist = list(serial.tools.list_ports.comports())
    for item in reversed(portlist):
        portstatus.set("Trying port " + item[0])
        top.update()
        try:
            ser = serial.Serial(item[0], 9600, timeout=0.5)
            time.sleep(0.2)
            ser.write(b'\x03')
            instr = ser.readline().decode()
            if len(instr) > 1 and instr[1] == '>':
                ser.timeout = 3
                portstatus.set("Connected to " + item[0])
                ser.write(b"VDC; RATE S; *IDN?\r\n")
                devicename = ser.readline().decode()
                DMM_Name.set(devicename.replace("\r", "").replace("\n", ""))
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
Button(top, width=11, text="Exit", command=Just_Exit).grid(row=9, column=0)

CJTemp.set("22")
DMMout.set("NO DATA")
DMM_Name.set("--------")

port = 'COM11'
try:
    ser2 = serial.Serial(port, 115200, timeout=0)
except:
    print(f'Serial port {port} is not available')
    for item in list(serial.tools.list_ports.comports()):
        print(item[0])

top.after(500, FindPort)
top.mainloop()

