import time

from machine import I2C, Pin
from neopixel import NeoPixel

PIN_ONBOARD_LED = 16
onboard_led_pin = Pin(PIN_ONBOARD_LED, Pin.OUT)


PIN_I2C_SDA = 26
PIN_I2C_SCL = 27
PIN_N_SLEEP_CELL_0 = 9
PIN_N_SLEEP_CELL_1 = 10
PIN_N_SLEEP_CELL_2 = 11  # U3/M3
PIN_N_SLEEP_CELL_3 = 12

PIN_N_FAULT_CELL_2 = 2  # U3/M3


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


REGISTER_ADDRESS_IC1_CONTROL = 0x01  # Control register address
REGISTER_ADDRESS_IC2_CONTROL = 0x02  # Control register address
REGISTER_ADDRESS_FAULT_STATUS_2 = 0x04  # Fault status register address

# HALF_STEP_SEQUENCE = [0x44, 0x4C, 0x0C, 0x2C, 0x24, 0x34, 0x14, 0x54]
HALF_STEP_SEQUENCE = [
    # 0b IN4 IN3 IN2 IN1
    0b1000,  # Sequence step 1
    0b1001,  # Sequence step 2
    0b0001,  # Sequence step 3
    0b0101,  # Sequence step 4
    0b0100,  # Sequence step 5
    0b0110,  # Sequence step 6
    0b0010,  # Sequence step 7
    0b1010,  # Sequence step 8
]

IC1_I2CBC_SELECT = 0b1  # Control via register instead of input pins.
IC1_MODE_4_INPUTS = 0b0  # 0b0=4-input interface.
IC1_TRQ_SETTING = 0b1  # 0b1=50% torque mode.

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


def write_register(address: int, register: int, value: int) -> None:
    """Write a single byte to a register on the DRV8847S."""
    print(f"write_register({address=}, {register=}, {value=}) ...")

    data = bytearray([register, value])
    i2c.writeto(address, data)


def read_from_register(address: int, register: int) -> int:
    """Read a single byte from a register on the DRV8847S."""
    i2c.writeto(address, bytearray([register]))
    data = i2c.readfrom(address, 1)
    val = data[0]
    print(
        f"read_from_register({address=}, {register=}) = {val} = 0x{val:x} = 0b{val:b} ..."
    )
    return val


def send_drive_command(
    i2c_addr: int, *, trq: int, step_value: int, i2cbc: int, mode: int
) -> None:
    """Send a drive command to the DRV8847S."""
    ic1_val = (trq << 7) | (step_value << 3) | (i2cbc << 2) | (mode << 1)
    write_register(i2c_addr, REGISTER_ADDRESS_IC1_CONTROL, ic1_val)


def drive_motor(
    step_period_sec: float,
    step_count: int,
    step_seq: list[int] = HALF_STEP_SEQUENCE,
    i2c_addr: int = DRV8847S_DEFAULT_I2C_ADDR,
) -> None:
    """Drive the motor."""
    # TODO: Support reverse direction.
    done_step_count = 0

    step_seq_run = step_seq[::-1] if step_count < 0 else step_seq
    abs_step_count = abs(step_count)

    while 1:
        for step_value in step_seq_run:
            # Enable TRQ = 50% torque mode (heat).
            send_drive_command(
                i2c_addr=i2c_addr,
                trq=IC1_TRQ_SETTING,
                step_value=step_value,
                i2cbc=IC1_I2CBC_SELECT,
                mode=IC1_MODE_4_INPUTS,
            )
            time.sleep(step_period_sec)
            done_step_count += 1

            if done_step_count >= abs_step_count:
                return


def disable_motor(i2c_addr: int = DRV8847S_DEFAULT_I2C_ADDR) -> None:
    """Disable the motor."""
    # Disable the motor.
    send_drive_command(
        i2c_addr=i2c_addr,
        trq=IC1_TRQ_SETTING,
        step_value=0,  # <- Set IN1=IN2 and IN3=IN4 to stop the motor.
        i2cbc=IC1_I2CBC_SELECT,
        mode=IC1_MODE_4_INPUTS,
    )


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

    # Might be 20 full steps per revolution.
    # 40 half steps per revolution (so 40 here).

    set_led_color(31, 31, 31)  # White.
    drive_motor(step_period_sec=0.02, step_count=-100)

    set_led_color(0, 31, 0)  # Green.
    drive_motor(step_period_sec=0.02, step_count=100)

    # Read the fault status register.
    fault_status_2 = read_from_register(
        DRV8847S_DEFAULT_I2C_ADDR, REGISTER_ADDRESS_FAULT_STATUS_2
    )
    if fault_status_2:
        print("Fault detected!")

    set_led_color(31, 0, 0)  # Red.
    disable_motor()
    time.sleep(2)


# Run `setup` and `loop`.
setup()
while True:
    loop()
