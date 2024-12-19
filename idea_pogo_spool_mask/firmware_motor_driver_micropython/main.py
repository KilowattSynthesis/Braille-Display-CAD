import time

from machine import I2C, Pin
from neopixel import NeoPixel

PIN_ONBOARD_LED = 16
onboard_led_pin = Pin(PIN_ONBOARD_LED, Pin.OUT)


PIN_I2C_SDA = 26
PIN_I2C_SCL = 27
PIN_N_SLEEP_CELL_0 = 9
PIN_N_SLEEP_CELL_1 = 10
PIN_N_SLEEP_CELL_2 = 11 # U3/M3
PIN_N_SLEEP_CELL_3 = 12

PIN_N_FAULT_CELL_2 = 2 # U3/M3


# References:
# - https://www.ti.com/lit/ds/symlink/drv8847.pdf
# - https://www.tij.co.jp/lit/ug/tidued1a/tidued1a.pdf (start around Page 14/35)

# Notes:
# - Set nSLEEP to 1 to use the device (or pull it up).
# - Pull nFAULT LOW to release/sleep them. Pull nFAULT HIGH to talk to them.
# - Reprogram the addresses one-by-one using nFAULT.

# 0x60 = 96
DRV8847S_DEFAULT_I2C_ADDR = 0x60  # 7-bit address

i2c = I2C(1, scl=Pin(PIN_I2C_SCL), sda=Pin(PIN_I2C_SDA), freq=400000)
# pin_nfault_2 = Pin(PIN_N_FAULT_CELL_2, Pin.IN, Pin.PULL_UP)


CONTROL_REG = 0x01   # Control register address
HALF_STEP_SEQUENCE = [0x44, 0x4C, 0x0C, 0x2C, 0x24, 0x34, 0x14, 0x54]

# Registers
# Table 7-15. I2C Registers
# | Addr | Acronym     | Register Name                | 7     | 6         | 5     | 4      | 3    | 2     | 1     | 0     | Access |
# |------|-------------|------------------------------|-------|-----------|-------|--------|------|-------|-------|-------|--------|
# | 0x00 | SLAVE_ADDR  | Slave Address                | RSVD  | SLAVE_ADDR|       |        |      |       |       |       | RW     |
# | 0x01 | IC1_CON     | IC1 Control                  | TRQ   | IN4       | IN3   | IN2    | IN1  | I2CBC | MODE  |       | RW     |
# | 0x02 | IC2_CON     | IC2 Control                  | CLRFLT| DISFLT    | RSVD  | DECAY  | OCPR | OLDOD | OLDFD | OLDBO | RW     |
# | 0x03 | SLR_STATUS1 | Slew Rate and Fault Status-1 | RSVD  | SLR       | RSVD  | nFAULT | OCP  | OLD   | TSDF  | UVLOF | RW     |
# | 0x04 | STATUS2     | Fault Status-2               | OLD4  | OLD3      | OLD2  | OLD1   | OCP4 | OCP3  | OCP2  | OCP1  | R      |
# 
# IC1_CON register (main one)
# Default: Mode = 0b00 means 4-input interface.
# Must set the input pin control.
# Must set I2CBC=0b1 (control via register instead of input pins).
# Should set TRQ=0b1 (50% torque) to minimize overheat.
# 
# IC2_CON register:
# Could explore DECAY: 0b0=25% fast (default) or 0b1=100% slow.
# Could explore SLR (slew rate): 0b0=150ns, 0b1=300ns


def write_register(address, register, value):
    """
    Write a single byte to a register on the DRV8847S.
    """
    print(f"write_register({address=}, {register=}, {value=}) ...")
    
    data = bytearray([register, value])
    i2c.writeto(address, data)


def drive_motor(step_period, step_count, step_seq = HALF_STEP_SEQUENCE, i2c_addr = DRV8847S_DEFAULT_I2C_ADDR):
    """
    Drive the motor.
    """
    # TODO: Support reverse direction.
    done_step_count = 0

    while 1:
        for step_value in step_seq:
            step_value_mod = step_value | (1 << 7)  # Enable TRQ = 50% mode.
            write_register(i2c_addr, CONTROL_REG, step_value_mod)
            time.sleep(step_period)
            done_step_count += 1
            
            if done_step_count >= step_count:
                return


def i2c_scan():
    print("Scanning I2C buses")
    i2c_scan_result = i2c.scan()
    print(f"I2C scan result: {i2c_scan_result}")



def setup() -> None:
    i2c_scan()

    print("Setting nSLEEP to PULLED UP")
    pin_nsleep_2 = Pin(PIN_N_SLEEP_CELL_2, Pin.IN, Pin.PULL_UP)
    i2c_scan()

    time.sleep_ms(500)


def set_led_color(r: int, g: int, b: int) -> None:
    """Display a color on the LED.

    Values should be between 0 and 255.
    """
    np = NeoPixel(onboard_led_pin, 1)
    np[0] = (r, g, b)
    np.write()


def loop() -> None:
    print("Motor demo")

    set_led_color(31, 0, 31)

    drive_motor(step_period=0.001, step_count=100)

    set_led_color(0, 31, 0)

    drive_motor(step_period=0.005, step_count=100)



# Run `setup` and `loop`.
setup()
while True:
    loop()
