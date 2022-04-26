#!/usr/bin/env python3

'''
Join experiments data
'''
import numpy as np
import pandas as pd
import easygui as eg

file_data = eg.fileopenbox(msg="Browse data", title=None, default='/home/spin/Esperimenti/*.npz',
                           filetypes=["*.npz"], multiple=True)
index = 0
text = ''
for file in file_data:
    try:
        # Visualizzazione della descrizione dell'esperimento
        with open(file.replace('.npz',''), "r", encoding='utf-8') as file_desc:
            text += file_desc.read() + '\n\n'
           
    except FileNotFoundError:
        print(f"Description of {file} not found.")

    # Caricamento dei dati
    data=np.load(file, allow_pickle=True)
    try:
        if index == 0:
            DT = data['datetime']
            V = data['voltage']
            R = data['resistance']
            T = data['temperature']
            I = data['current_source']
            J = data['current_density']
            E = data['electric_field']
            RHO = data['resistivity']
        else:
            DT = np.append(DT, data['datetime'], axis=0)
            V = np.append(V, data['voltage'], axis=0)
            R = np.append(R, data['resistance'], axis=0)
            T = np.append(T, data['temperature'], axis=0)
            I = np.append(I, data['current_source'], axis=0)
            J = np.append(J, data['current_density'], axis=0)
            E = np.append(E, data['electric_field'], axis=0)
            RHO = np.append(RHO, data['resistivity'], axis=0)
        index += 1
    except KeyError:
        pass

if len(file_data) > 0:
    path_file = file_data[0].replace('.npz','-joined')
    
    # Salvataggio descrizione
    print(f"Save experiments description {path_file}")
    with open(path_file, "w", encoding='utf-8') as file_desc:
        file_desc.write(text)

    # Salvataggio dati formato numpy
    print(f"Save data in numpy format {path_file}.npz")
    np.savez_compressed(path_file, datetime=DT, temperature=T,
                        voltage=V, resistance=R, current_source=I,
                        electric_field=E, current_density=J,
                        resistivity=RHO)

    # Salvataggio dati formato csv
    csv_path = path_file + ".csv"
    print(f"Save data in CSV format {csv_path}")
    data = pd.DataFrame(np.stack((T, V, R, I, E, RHO, J), axis=-1),
           columns=['Temperature [K]', 'Voltage [V]', 'Resistance [𝛀]', 'Current Source [A]', \
    'Electric Field [V/cm]', 'Restivity [𝛀 cm]', 'Current Density [A/cm2]'])
    data.to_csv(csv_path, index=False)



