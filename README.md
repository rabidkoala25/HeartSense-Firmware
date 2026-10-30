# HeartSense firmware

This is the code that runs on the Pico for my HeartSense magnetic field meter.

## what it does

- reads the magnetic field strength off the MMC5603 sensor
- shows a menu on the little OLED that you scroll through with the ANO wheel
  (spin to move, press in to pick, press left to go back)
- Live Field screen: shows the field as a big number in uT, a bar, and a
  green/red light. if the field gets too high it turns red and beeps
- Calibrate screen: you spin the device around and it figures out the offset
  from nearby metal so the readings are more accurate
- About screen, nothing exciting

## the files

- `main.py` - runs when it turns on, sets everything up and runs the menu
- `config.py` - all the pin numbers and addresses in one place
- `magnetometer.py` - talks to the MMC5603 sensor
- `oled.py` - draws to the screen
- `ano_wheel.py` - reads the scroll wheel and its buttons
- `outputs.py` - the buzzer and the RGB led
- `ui.py` - the smooth scrolling menu
- `screens.py` - the live/calibrate/about screens

## putting it on the Pico

copy all the .py files onto the Pico (I use Thonny). main.py runs by itself
when you plug it in. you need a MicroPython build that has neopixel and
framebuf but the normal Pico one does.

## how it's wired

| thing        | Pico pin      |
|--------------|---------------|
| buzzer       | GP2 (pin 4)   |
| neopixel     | GP3 (pin 5)   |
| I2C SDA      | GP4 (pin 6)   |
| I2C SCL      | GP5 (pin 7)   |

the sensor, OLED and wheel all share the same two I2C wires.
