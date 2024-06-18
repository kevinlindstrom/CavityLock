"""
kpz101_pythonnet
==================

An example of using the .NET API with the pythonnet package for controlling a KPZ101
"""
import os
import time
import sys
import clr
import numpy as np

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.PiezoCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.KCube.PiezoCLI import *
from System import Decimal  # necessary for real world units
# from decimal import *

# Sweep Up and Down
def pizeoSweep(device, Vmax, step, delay=0.5, N=1):
    V = np.arange(0, float(Decimal.ToDouble(Vmax)), step)
    print(V)
    i = 0
    while i < N:
        i += 1
        for v in V:
            v = Decimal(v)
            if v != Decimal(0) and v <= Vmax:
                device.SetOutputVoltage(v)
                time.sleep(delay)
            else:
                print(f'Voltage must be between 0 and {Vmax}')
        for v in np.flip(V):
            v = Decimal(v)
            if v != Decimal(0) and v <= Vmax:
                device.SetOutputVoltage(v)
                time.sleep(delay)
            else:
                print(f'Voltage must be between 0 and {Vmax}')


def main():
    """The main entry point for the application"""

    # Uncomment this line if you are using
    # SimulationManager.Instance.InitializeSimulations()

    try:

        DeviceManagerCLI.BuildDeviceList()

        # create new device
        serial_no = "29503050"  # Replace this line with your device's serial number
        Vstep = 0.5 # KP101 voltage step size

        # Connect, begin polling, and enable
        device = KCubePiezo.CreateKCubePiezo(serial_no)

        device.Connect(serial_no)

        # Get Device Information and display description
        device_info = device.GetDeviceInfo()
        print(device_info.Description)

        # Start polling and enable
        device.StartPolling(50)  #250ms polling rate default
        time.sleep(10) # default 25 s
        device.EnableDevice()
        time.sleep(0.25)  # Wait for device to enable

        if not device.IsSettingsInitialized():
            device.WaitForSettingsInitialized(5000)  # 10 second timeout
            assert device.IsSettingsInitialized() is True

        # Load the device configuration
        device_config = device.GetPiezoConfiguration(serial_no)

        # This shows how to obtain the device settings
        device_settings = device.PiezoDeviceSettings

        # Set Max Voltage to 100
        device.SetMaxOutputVoltage(Decimal(100))

        # Set the Zero point of the device
        print("Setting Zero Point")
        device.SetZero()

        # Get the maximum voltage output of the KPZ
        max_voltage = device.GetMaxOutputVoltage()  # This is stored as a .NET decimal
        print(max_voltage)
        print(type(max_voltage))

        # Voltage sweep
        pizeoSweep(device, Decimal(80), Vstep, delay=0.0025, N=2000)


        # Stop Polling and Disconnect
        device.StopPolling()
        device.Disconnect()
        time.sleep(0.25)
    except Exception as e:
        print(e)

    # Uncomment this line if you are using Simulations
    # SimulationManager.Instance.UnitializeSimulations()
    ...


if __name__ == "__main__":
    main()
