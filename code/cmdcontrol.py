import RPi.GPIO as GPIO
import board
import threading
import time
import csv
import os
import queue
import adafruit_bme280.basic as adafruit_bme280
from adafruit_bmp280 import Adafruit_BMP280_I2C

# Pin Definitions & Constants
FANPIN = 17
HEATERPIN = 27
LOG_FILE = "sensor_data.csv"

# Active Hardware Logic (Active-LOW Relays)
HEATER_ON = GPIO.LOW
HEATER_OFF = GPIO.HIGH

# Global State Variables
current_goal = 0.0
running = True
current_task = "Idle"
auto_paused = False
interrupt_auto = False

# Threading Locks (Prevents I2C Collisions & File Corruption)
i2c_lock = threading.Lock()
csv_lock = threading.Lock()

# Task Queue Setup
command_queue = queue.Queue()
history_queue = []

# GPIO Initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(FANPIN, GPIO.OUT)
GPIO.setup(HEATERPIN, GPIO.OUT)
GPIO.output(FANPIN, GPIO.LOW)
GPIO.output(HEATERPIN, HEATER_OFF)

# Dual I2C Sensor Initialization
i2c = board.I2C()

# Internal Sensor: BME280 (Default Address 0x76)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
bme280.sea_level_pressure = 1013.25

# External Sensor: BMP280 (SDO connected to VCC for Address 0x77)
bmp280_out = Adafruit_BMP280_I2C(i2c, address=0x77)
bmp280_out.sea_level_pressure = 1013.25

def emergency_stop_outputs():
    """Forces all relay outputs into a safe OFF state."""
    GPIO.output(HEATERPIN, HEATER_OFF)
    GPIO.output(FANPIN, GPIO.LOW)

def read_sensors_safe():
    """Thread-safe acquisition of all environmental telemetry."""
    with i2c_lock:
        t_in = bme280.temperature
        h_in = bme280.relative_humidity
        p_in = bme280.pressure
        t_out = bmp280_out.temperature
        p_out = bmp280_out.pressure
    return t_in, h_in, p_in, t_out, p_out

def write_to_csv(data_list):
    """Thread-safe CSV logging helper."""
    with csv_lock:
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Timestamp", 
                    "Internal_Temp_C", 
                    "Outside_Temp_C", 
                    "Internal_Humidity_%", 
                    "Internal_Pressure_hPa", 
                    "External_Pressure_hPa", 
                    "Heater_Status"
                ])
            writer.writerow(data_list)

def log_data():
    """Periodic logging worker running at 5-second intervals."""
    while running:
        try:
            t_in, h_in, p_in, t_out, p_out = read_sensors_safe()
            h_s = 1 if GPIO.input(HEATERPIN) == HEATER_ON else 0
            write_to_csv([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{t_in:.2f}", f"{t_out:.2f}",
                f"{h_in:.2f}",
                f"{p_in:.2f}", f"{p_out:.2f}",
                h_s
            ])
        except Exception as e:
            write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"SENSOR_READ_ERROR: {e}", "", "", "", "", ""])
        time.sleep(5)

def display_status():
    """Real-time single-line terminal monitor."""
    global running, current_task
    print("\n--- System Online ---")
    while running:
        try:
            with i2c_lock:
                t_in = bme280.temperature
                t_out = bmp280_out.temperature
            h_s = "ON" if GPIO.input(HEATERPIN) == HEATER_ON else "OFF"
            next_tasks = list(command_queue.queue)[:2]
            queue_str = " -> ".join(next_tasks) if next_tasks else "None"
            print(f"\r[IN: {t_in:.2f}°C | OUT: {t_out:.2f}°C] [HEAT: {h_s}] | DOING: {current_task} | NEXT: {queue_str}      ", end="", flush=True)
        except Exception: 
            pass
        time.sleep(2)

def mission_runner():
    """Main execution engine processing automated command queues."""
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
                goal = max(16.0, min(32.0, goal))  # Enforce thermal boundary limits
                current_goal = goal
                
                start_wait = time.time()
                timeout_seconds = 90 * 60  # 90-minute safety threshold
                
                while running and not interrupt_auto:
                    with i2c_lock:
                        current_t = bme280.temperature
                    
                    if abs(current_t - current_goal) < 0.5:
                        write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"EVENT: Reached {current_goal}C", "", "", "", "", ""])
                        break
                    
                    if (time.time() - start_wait) > timeout_seconds:
                        emergency_stop_outputs()
                        write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"TIMEOUT: Goal {current_goal}C failed. HEATER OFF", "", "", "", "", ""])
                        print(f"\n[ALERT] Timeout reached. Outputs forced OFF.")
                        break
                    time.sleep(1)
                    
            elif cmd_type == "time":
                seconds = int(float(parts[1]) * 60)
                for _ in range(seconds):
                    if not running or interrupt_auto: break
                    while auto_paused: time.sleep(0.5)
                    time.sleep(1)
                    
            elif cmd_type == "heater":
                GPIO.output(HEATERPIN, HEATER_ON if parts[1] == "on" else HEATER_OFF)
            elif cmd_type == "fan":
                GPIO.output(FANPIN, GPIO.HIGH if parts[1] == "on" else GPIO.LOW)
            elif cmd_type == "line":
                write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), "-"*20, "---", "---", "---", "---", "-"])
            elif cmd_type == "note":
                note_text = " ".join(parts[1:])
                write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"NOTE: {note_text}", "", "", "", "", ""])

        except Exception as e:
            print(f"\n[ERROR] Task '{task}' failed: {e}")

        history_queue.append(task)
        if len(history_queue) > 10: 
            history_queue.pop(0)
            
        command_queue.task_done()
        if interrupt_auto: 
            interrupt_auto = False

# Background Workers
threading.Thread(target=display_status, daemon=True).start()
threading.Thread(target=log_data, daemon=True).start()
threading.Thread(target=mission_runner, daemon=True).start()

# Interactive Command Interface
try:
    while True:
        cmd = input().lower().strip()
        if not cmd: 
            continue

        if cmd.startswith("auto"):
            auto_paused = False
            interrupt_auto = False
            raw_cmds = cmd.split()[1:]
            i = 0
            while i < len(raw_cmds):
                c = raw_cmds[i]
                if c in ["temp", "time", "heater", "fan", "note"] and i + 1 < len(raw_cmds):
                    command_queue.put(f"{c} {raw_cmds[i+1]}")
                    i += 2
                elif c == "line":
                    command_queue.put("line")
                    i += 1
                else: 
                    i += 1

        elif cmd == "qview":
            print(f"\n\n--- QUEUE STATUS ---\nDONE: {history_queue[-5:]}\nDOING: {current_task}\nTO DO: {list(command_queue.queue)}\n")

        elif cmd == "qclear":
            with command_queue.mutex:
                command_queue.queue.clear()
            print(f"\n[SYSTEM] Command queue cleared. Finishing current task: {current_task}")

        elif cmd == "qdel":
            interrupt_auto = True
            with command_queue.mutex: 
                command_queue.queue.clear()
            emergency_stop_outputs()
            print("\n[SYSTEM] Queue purged and all active outputs forced OFF.")

        elif cmd == "qpause": 
            auto_paused = True
        elif cmd == "line": 
            write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), "-"*20, "", "", "", "", ""])
        elif cmd.startswith("note "): 
            write_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), f"NOTE: {cmd[5:]}", "", "", "", "", ""])
        elif cmd in ["fan on", "fan off"]: 
            GPIO.output(FANPIN, GPIO.HIGH if "on" in cmd else GPIO.LOW)
        elif cmd in ["heater on", "heater off"]: 
            GPIO.output(HEATERPIN, HEATER_ON if "on" in cmd else HEATER_OFF)
        elif cmd == "exit":
            running = False
            break

finally:
    emergency_stop_outputs()
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
