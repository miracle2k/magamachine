try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
import time


LED_PIN = 2
BUTTON_PIN = 23

def setup():
    if not GPIO:
        return
        
    GPIO.setmode(GPIO.BCM)

    # The button input
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # The LED output
    GPIO.setup(LED_PIN, GPIO.OUT)


def query():
    if not GPIO:
        return

    state = GPIO.input(23)
    if state == False:
        return True
    return False


def set_led(on):
    if not GPIO:
        return

    GPIO.output(LED_PIN, on)


def cleanup():
    if not GPIO:
        return
    
    GPIO.cleanup()
