import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


file = "Data/slowLinearSlope4.csv"
fntSz= 30

df = pd.read_csv(file)
print(df)

t = np.array(df["time (s)"])
pdmV = np.array(df["PD Voltage (mV)"])
piezomV =  np.array(df["Piezo Monitor (mV)"])

plt.plot(t, piezomV)
plt.plot(t, pdmV)
plt.xlabel('Time (s)', fontsize=fntSz)
plt.ylabel('Voltage (mV)', fontsize=fntSz)
plt.title(f'Piezo and Photodiode Voltage\n{file}', fontsize=fntSz)
plt.grid()
plt.show()

