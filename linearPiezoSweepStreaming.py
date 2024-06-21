import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import time
import pandas as pd
import math


# Output file
file = "slowLinearSlope4.csv"


def getTimeUnitFactor(timeEnum):
    if timeEnum <= 5 and timeEnum >= 0:
        return [1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1][timeEnum]
    else:
        raise ValueError('Time unit enum index out of range')

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open PicoScope 5000 Series device
# Resolution set to 12 Bit
resolution = ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
# Returns handle to chandle for use in future API functions
status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(chandle), None, resolution)

try:
    assert_pico_ok(status["openunit"])
except: # PicoNotOkError:

    powerStatus = status["openunit"]

    if powerStatus == 286:
        status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
    elif powerStatus == 282:
        status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
    else:
        raise

    assert_pico_ok(status["changePowerSource"])

# --------------------------------------------------------------------- Ramp AWG
wavetype = ctypes.c_int32(3)
sweepType = ctypes.c_int32(0)
triggertype = ctypes.c_int32(0)
triggerSource = ctypes.c_int32(0)
freq = 0.2

status["setSigGenBuiltInV2"] = ps.ps5000aSetSigGenBuiltInV2(chandle, 
                                                            1000000, 2000000, 
                                                            wavetype, freq, freq, 
                                                            0, 1, sweepType, 0,
                                                            0, 0, triggertype,
                                                            triggerSource, 0)
assert_pico_ok(status["setSigGenBuiltInV2"])


# -------------------------------------------------------------------- Streaming
enabled = 1
disabled = 0
analogue_offset = 0.0

# Set up channel C
channel_rangeC = ps.PS5000A_RANGE['PS5000A_10V']
status["setChC"] = ps.ps5000aSetChannel(chandle,
                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_C'],
                                        enabled,
                                        ps.PS5000A_COUPLING['PS5000A_DC'],
                                        channel_rangeC,
                                        analogue_offset)
assert_pico_ok(status["setChC"])

# Set up channel D
channel_rangeD = ps.PS5000A_RANGE['PS5000A_20V']
status["setChD"] = ps.ps5000aSetChannel(chandle,
                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_B'],
                                        enabled,
                                        ps.PS5000A_COUPLING['PS5000A_DC'],
                                        channel_rangeD,
                                        analogue_offset)
assert_pico_ok(status["setChD"])

# Size of capture
sizeOfOneBuffer = 500
numBuffersToCapture = 5000
totalSamples = sizeOfOneBuffer * numBuffersToCapture

# Create buffers ready for assigning pointers for data collection
bufferCMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
bufferDMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)

memory_segment = 0

# Set data buffer location for data collection from channel C
status["setDataBuffersC"] = ps.ps5000aSetDataBuffers(chandle,
                                                     ps.PS5000A_CHANNEL['PS5000A_CHANNEL_C'],
                                                     bufferCMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                     None,
                                                     sizeOfOneBuffer,
                                                     memory_segment,
                                                     ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
assert_pico_ok(status["setDataBuffersC"])

# Set data buffer location for data collection from channel D
status["setDataBuffersD"] = ps.ps5000aSetDataBuffers(chandle,
                                                     ps.PS5000A_CHANNEL['PS5000A_CHANNEL_D'],
                                                     bufferDMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                     None,
                                                     sizeOfOneBuffer,
                                                     memory_segment,
                                                     ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
assert_pico_ok(status["setDataBuffersD"])

# Begin streaming mode:
sampleInterval = ctypes.c_int32(20)
sampleUnits = ps.PS5000A_TIME_UNITS['PS5000A_US']
print(sampleUnits)
# We are not triggering:
maxPreTriggerSamples = 0
autoStopOn = 1
# No downsampling:
downsampleRatio = 1
status["runStreaming"] = ps.ps5000aRunStreaming(chandle,
                                                ctypes.byref(sampleInterval),
                                                sampleUnits,
                                                maxPreTriggerSamples,
                                                totalSamples,
                                                autoStopOn,
                                                downsampleRatio,
                                                ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'],
                                                sizeOfOneBuffer)
assert_pico_ok(status["runStreaming"])

actualSampleInterval = sampleInterval.value*getTimeUnitFactor(sampleUnits)


print("Capturing at sample interval %s s" % actualSampleInterval)

# We need a big buffer, not registered with the driver, to keep our complete capture in.
bufferCompleteC = np.zeros(shape=totalSamples, dtype=np.int16)
bufferCompleteD = np.zeros(shape=totalSamples, dtype=np.int16)
nextSample = 0
autoStopOuter = False
wasCalledBack = False


def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
    global nextSample, autoStopOuter, wasCalledBack
    wasCalledBack = True
    destEnd = nextSample + noOfSamples
    sourceEnd = startIndex + noOfSamples
    bufferCompleteC[nextSample:destEnd] = bufferCMax[startIndex:sourceEnd]
    bufferCompleteD[nextSample:destEnd] = bufferDMax[startIndex:sourceEnd]
    nextSample += noOfSamples
    if autoStop:
        autoStopOuter = True


# Convert the python function into a C function pointer.
cFuncPtr = ps.StreamingReadyType(streaming_callback)

# Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
while nextSample < totalSamples and not autoStopOuter:
    wasCalledBack = False
    status["getStreamingLastestValues"] = ps.ps5000aGetStreamingLatestValues(chandle, cFuncPtr, None)
    if not wasCalledBack:
        # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
        # again.
        time.sleep(0.01)

print("Done grabbing values.")

# Find maximum ADC count value
# pointer to value = ctypes.byref(maxADC)
maxADC = ctypes.c_int16()
status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
assert_pico_ok(status["maximumValue"])

# Convert ADC counts data to mV
adc2mVChCMax = adc2mV(bufferCompleteC.astype(int), channel_rangeC, maxADC)
adc2mVChDMax = adc2mV(bufferCompleteD.astype(int), channel_rangeD, maxADC)

# Create time data
time = np.linspace(0, (totalSamples - 1) * actualSampleInterval, totalSamples)

# Plot data from channel A and B
plt.plot(time, adc2mVChCMax[:])
plt.plot(time, adc2mVChDMax[:])
plt.xlabel('Time (s)')
plt.ylabel('Voltage (mV)')
plt.show()

# Stop the scope
# handle = chandle
status["stop"] = ps.ps5000aStop(chandle)
assert_pico_ok(status["stop"])

# Disconnect the scope
# handle = chandle
status["close"] = ps.ps5000aCloseUnit(chandle)
assert_pico_ok(status["close"])

# Display status returns
print(status)

df = pd.DataFrame({"time (s)" : time, 
                   "Piezo Monitor (mV)" : adc2mVChCMax, 
                   "PD Voltage (mV)" : adc2mVChDMax})
df.to_csv(file, index=False)
