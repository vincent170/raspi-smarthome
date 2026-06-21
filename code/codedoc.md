# Welcome to the Smart Home Club Code Documentation!

This explains `cmdcontrol.py` from scratch. Feel free to work on this yourself and add suitable improvements where you deem necessary.

---

## What does this actually do?

This code runs on a **Raspberry Pi Model 4** and:
- Reads the temperature off a **BME280** every 5 seconds
- Turns a heater on/off through 2 GPIO pins that are connected to the Pi
- Adds the logs to a CSV file
- Allows you to type commands (More on this later)
- Does all this **at the same time**

## Imports (libraries)
 
```python
import RPi.GPIO as GPIO
import board
import threading
import time
import csv
import os
import queue
from adafruit_bme280 import basic as adafruit_bme280
```
 
`RPi.GPIO` lets python flip between HIGH and LOQ to turn things on and off. `board` just helps `adafruit_bme280` find the I2C bus on your specific Pi. The rest — `threading`, `time`, `csv`, `os`, `queue` — are all standard Python, nothing specific: running things in parallel, pausing, writing files, checking if a file exists, and managing a list, in that order.

## Setup
 
```python
FANPIN = 17
HEATERPIN = 27
...
HEATER_ON = GPIO.LOW
HEATER_OFF = GPIO.HIGH
```
The fan and heater pins are easy to be toggled. They can just be adjusted by redefining the variable. What's interesting is LOW and HIGH are actually inverted. Usually, HIGH turns things on and LOW turns things off, however we have used a transistor so the signals are flipped.

## Pins and sensor go live
 
```python
GPIO.setmode(GPIO.BCM)
GPIO.setup(FANPIN, GPIO.OUT)
GPIO.setup(HEATERPIN, GPIO.OUT)
GPIO.output(FANPIN, GPIO.LOW)
GPIO.output(HEATERPIN, HEATER_OFF)
```

Both pins get declared as outputs, then both get switched off immediately. That last line does more than it looks; if it had been left as plain `GPIO.LOW` after your transistor change, the heater would switch ON the instant the script starts, since LOW is now "on." Using `HEATER_OFF` instead of `GPIO.LOW` prevents this from happening.

## write_to_csv()
 
Opens the log file, adds a header row the first time it's ever run, then appends whatever row you hand it. `with open(...) as f:` is just the safe way to open files in Python and it closes the file automatically even if something goes wrong halfway through.

## log_data() — thread 1
 
Every 5 seconds: reads temp, humidity, pressure, checks whether each pin's on or off, writes a row. The heater check is the one worth looking at closely:
 
```python
h_s = 1 if GPIO.input(HEATERPIN) == HEATER_ON else 0
```
 
It compares the pin's voltage against `HEATER_ON` rather than just asking if it's HIGH because HIGH doesn't mean on anymore. This allows the log to be accurate for the future.
 
The whole loop sits in a `try / except: pass`, so if reading the sensor brings an error, it just tries again in 5 seconds instead of crashing. It could be improved as the code just goes on if there was sommething wrong.....

## display_status() — thread 2
 
**Purely cosmetic**: prints a live line to the terminal every 2 seconds. The `\r` and `end=""` are what make it overwrite itself in place instead of spamming a new line every cycle. Same `== HEATER_ON` comparison as above so the screen displays REAL values.

## mission_runner() — thread 3, the mastermind of the operation
 
This is the function that actually does the things. It pulls the job off the queue (`"temp 28"`, `"heater on"`, etc you get the point), splits it into words, and branches on the first one.
 
**`temp <value>`** — locks your target between 18°C and 30°C regardless of what you typed, then loops checking the sensor once a second until it's within 0.5°C of the target, or until 90 minutes pass with no luck. On timeout:
 
```python
GPIO.output(HEATERPIN, HEATER_OFF)
```
 
This is the line that would've been a bug if left as `GPIO.LOW`. Before, a "force the heater off" failsafe would've turned it on. Worth documenting this error, useful for future prevention.
 
**`heater on` / `heater off`** — uses `HEATER_ON` / `HEATER_OFF`, same as everywhere else.
 
**`fan on` / `fan off`** — still plain `GPIO.HIGH` / `GPIO.LOW`, not inverted since the fan **does not have a transistor**.
 
**`line` / `note`** — write markers into the CSV for reference.
 
Unlike the other two threads, the errors here get printed out (`[ERROR] Task '...' failed: ...`), prevents experiments from going on and failing...

## Starting everything
 
```python
threading.Thread(target=display_status, daemon=True).start()
threading.Thread(target=log_data, daemon=True).start()
threading.Thread(target=mission_runner, daemon=True).start()
```
 
When the main thread is killed, these threads **are killed as well** instead of running in the background.

## The command loop
 
Everything below this reads what you type, makes it lowercase and trims it, then matches it against the list of known commands — `auto ...`, `qview`, `qpause`, `qdel`, `fan on/off`, `heater on/off`, `exit`. `auto` is the fiddliest: it walks through your words two at a time, then combines each pair back into a string like `"temp 28"`, and adds it on the queue for `mission_runner` to work through.

## Shutting down
 
```python
finally:
    GPIO.cleanup()
```

No matter how the script is killed, it will always reset the pins to a safe spot. This is important for safety, especially while dealing with heaters.

## Commands for reference

| Command | The function |
|---|---|
| `heater on` | Turns the heater on |
| `heater off` | Turns the heater on |
| `fan on` | Turns the fan on |
| `fan off` | Turns the fan off |
| `note <text>` | Allows you to add a comment onto the CSV file |
| `line` | Allows you to add a space to the CSV file |
| `auto <sequence>` | Allows you to write a sequence for autonomous |
| `qview` | Allows you to view the current autonomous queue |
| `qclear` | Clears the current autonomous queue |
| `qpause` | Pauses the autonomous queue |
| `qdel` | Deletes the autonomous queue |
| `exit` | Kills the program |
 

## Future fixes

1. The silent `exceptL pass` blocks do not display the bugs for you unlike the `mission_runner` function
