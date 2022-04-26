#!/usr/bin/env python3

'''

'''
import numpy as np
import easygui as eg
import pandas as pd

file_name = eg.fileopenbox(msg="Browse data", title=None, default='/home/spin/Esperimenti/*.npz', filetypes=["*.npz"], multiple=False)
data=np.load(file_name, allow_pickle=True)
file_npz = file_name.replace(".npz", "") + "_a.npz"
file_csv = file_name.replace(".npz", "") + "_a.csv"
try:
    DT=data['datetime']
    V=data['voltage']
    R=data['resistance']
    T=data['temperature']
    I=data['current_source']
#    J=data['current_density']
#    E=data['electric_field']
#    RHO=data['resistivity']
except KeyError:
    pass

area=4.807e-2
length=0.2376e-1
E=V/length
J=I/area
RHO=E/J

# Salvataggio dati formato numpy
np.savez_compressed(file_npz, datetime=DT, temperature=T,
                    voltage=V, resistance=R, current_source=I,
                    electric_field=E, current_density=J,
                    resistivity=RHO)

# Salvataggio dati formato csv
data = pd.DataFrame(np.stack((T, V, R, I, E, RHO, J), axis=-1),
columns=['Temperature [K]', 'Voltage [V]', 'Resistance [Ohm]', 'Current Source [A]', 'Electric Field [V cm]', 'Restivity [Ohm cm]', 'Current Density [A/cm2]'])
data.to_csv(file_csv, index=False)



