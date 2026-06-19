import RPi.GPIO as GPIO
import board
import threading
import time
import csv
import os
import queue
from adafruit_bme280 import basic as adafruit_bme280

#super fun functions
FANPIN = 17
HEATERPIN = 27
LOG_FILE = "sensor_data.csv"
current_goal = 0.0#tracks active temp to go to
running = True


HEATER_ON = GPIO.LOW
HEATER_OFF = GPIO.HIGH

#queue and state vars
command_queue = queue.Queue()
history_queue = []
current_task = "Idle"
auto_paused = False
interrupt_auto = False

#hardware stuff
GPIO.setmode(GPIO.BCM)
GPIO.setup(FANPIN, GPIO.OUT)
GPIO.setup(HEATERPIN, GPIO.OUT)
GPIO.output(FANPIN, GPIO.LOW)
GPIO.output(HEATERPIN, HEATER_OFF)

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
bme280.sea_level_pressure = 1013.25

def write_to_csv(data_list):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Temp_C", "Humidity_%", "Pressure_hPa", "Current_Goal", "Fan_Status", "Heater_Status"])
        writer.writerow(data_list)

#data log to csv
def log_data():
    while running:
        try:
            t, h, p = bme280.temperature, bme280.relative_humidity, bme280.pressure
            f_s = 1 if GPIO.input(FANPIN) else 0
            h_s = 1 if GPIO.input(HEATERPIN) == HEATER_ON else 0
            write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"{t:.2f}", f"{h:.2f}", f"{p:.2f}", current_goal, f_s, h_s])
        except: pass 
        time.sleep(5)

def display_status():
    global running, current_task
    print("\n--- System Online ---")
    while running:
        try:
            t = bme280.temperature
            f_s = "ON" if GPIO.input(FANPIN) else "OFF"
            h_s = "ON" if GPIO.input(HEATERPIN) == HEATER_ON else "OFF"
            next_tasks = list(command_queue.queue)[:2] 
            queue_str = " -> ".join(next_tasks) if next_tasks else "None"
            #shwo current temp
            print(f"\r[TEMP: {t:.2f}°C] [FAN: {f_s} | HEAT: {h_s}] | DOING: {current_task} | NEXT: {queue_str}      ", end="")
        except: pass
        time.sleep(2)

def mission_runner():
    global auto_paused, interrupt_auto, current_goal, current_task
    while running:
        if auto_paused or command_queue.empty():
            current_task = "Paused" if auto_paused else "Idle"
            current_goal = 0.0
            time.sleep(0.5)
            continue
            
        task = command_queue.get()
        current_task = task
        parts = task.split()
        cmd_type = parts[0]
        
        try:
            if cmd_type == "temp":
                goal = float(parts[1])
                #Safety limits ---------------------------- CHANGE THIS, 28 I THINK?
                if goal > 30.0: goal = 30.0
                elif goal < 18.0: goal = 18.0
                current_goal = goal
                
                start_wait = time.time()
                timeout_seconds = 90 * 60 
                
                while running and not interrupt_auto:
                    current_t = bme280.temperature
                    if abs(current_t - current_goal) < 0.5:
                        write_to_csv([f"EVENT: Reached {current_goal}C", "", "", "", "", "", ""])
                        break
                    
                    if (time.time() - start_wait) > timeout_seconds:
                        GPIO.output(HEATERPIN, HEATER_OFF)
                        write_to_csv([f"TIMEOUT: Goal {current_goal}C failed. HEATER OFF", "", "", "", "", "", ""])
                        print(f"\n[ALERT] Timeout reached. Heater forced OFF.")
                        break
                    time.sleep(1)
                    
            elif cmd_type == "time":
                seconds = int(float(parts[1]) * 60)
                for s in range(seconds):
                    if not running or interrupt_auto: break
                    while auto_paused: time.sleep(0.5)
                    time.sleep(1)
                    
            elif cmd_type == "heater":
                GPIO.output(HEATERPIN, HEATER_ON if parts[1] == "on" else HEATER_OFF)
            elif cmd_type == "fan":
                GPIO.output(FANPIN, GPIO.HIGH if parts[1] == "on" else GPIO.LOW)
            elif cmd_type == "line":
                write_to_csv(["-"*20, "---", "---", "---", "---", "-", "-"])
            elif cmd_type == "note":
                write_to_csv([f"NOTE: {parts[1]}", "", "", "", "", "", ""])

        except Exception as e:
            print(f"\n[ERROR] Task '{task}' failed: {e}")

        history_queue.append(task)
        if len(history_queue) > 10: history_queue.pop(0)
        command_queue.task_done()
        if interrupt_auto: interrupt_auto = False

#Controller
threading.Thread(target=display_status, daemon=True).start()
threading.Thread(target=log_data, daemon=True).start()
threading.Thread(target=mission_runner, daemon=True).start()

try:
    while True:
        cmd = input().lower().strip()
        if not cmd: continue

        if cmd.startswith("auto"):#auto function
            auto_paused = False
            interrupt_auto = False
            raw_cmds = cmd.split()[1:]
            i = 0
            while i < len(raw_cmds):
                c = raw_cmds[i]
                if c in ["temp", "time", "heater", "fan", "note"] and i+1 < len(raw_cmds):
                    command_queue.put(f"{c} {raw_cmds[i+1]}")
                    i += 2
                elif c == "line":
                    command_queue.put("line")
                    i += 1
                else: i += 1

        elif cmd == "qview":#command to view queue status and history
            print(f"\n\n--- QUEUE STATUS ---\nDONE: {history_queue[-5:]}\nDOING: {current_task}\nTO DO: {list(command_queue.queue)}\n")

        elif cmd == "qclear":#clears list but keeps current task going
            with command_queue.mutex:
                command_queue.queue.clear()
            print(f"\n[SYSTEM] Command queue cleared. Finishing current task: {current_task}")

        elif cmd == "qdel":#deletes EVERYTHING list related, even current task
            interrupt_auto = True
            with command_queue.mutex: command_queue.queue.clear()
        elif cmd == "qpause": auto_paused = True
        elif cmd == "line": write_to_csv(["-"*20, "", "", "", "", "", ""])
        elif cmd.startswith("note "): write_to_csv([f"NOTE: {cmd[5:]}", "", "", "", "", "", ""])
        elif cmd in ["fan on", "fan off"]: GPIO.output(FANPIN, GPIO.HIGH if "on" in cmd else GPIO.LOW)
        elif cmd in ["heater on", "heater off"]: GPIO.output(HEATERPIN, HEATER_ON if "on" in cmd else HEATER_OFF)
        elif cmd == "exit":
            running = False
            break
finally:
    GPIO.cleanup()

'''
HOW TO USE THIS

Manual Commands:
fan/heater on/off
line
note hi_there
exit

Auto sequence commands: (Add word auto at start)
temp 28
time 10
all other manual ones

'Debug' queue commands:
qview - Shows status report
qpause - Pauses queue and sequence (auto to resume)
qdel - Delete queue and stop current task

Example cases:
'I want to heat to 27C and then wait 2 minutes, note down on csv file  and hold for 15 more minutes and then note it's done'
auto heater on temp 27 time 2 note reached_27 time 15 note done
'I want to repeat heating to 28C and then leaving it to cool to 23C, wait for 5 minutes and repeat'
auto heater on temp 28 heater off temp 23 note cycle1_done time 5 .... etc
'I want to just see how much you can heat in 1hr and then cool down to starting temp of 22'
auto heater on time 60 heater off temp 22 note test_done

'''