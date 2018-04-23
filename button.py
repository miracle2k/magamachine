import RPi.GPIO as GPIO
import time

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def query():
    state = GPIO.input(23)
    if state == False:
        return True
    return False

def cleanup():
    GPIO.cleanup()
