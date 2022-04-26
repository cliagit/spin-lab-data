#!/usr/bin/env python3

'''
Plotting experiment data
'''
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
import easygui as eg

# Stile della finestra dei grafici
# plt.style.use('dark_background')

file_data = eg.fileopenbox(msg="Browse data", title=None, default='/home/spin/Esperimenti/*.npz',
                           filetypes=["*.npz"], multiple=True)
index = 0
for file in file_data:
    try:
        # Visualizzazione della descrizione dell'esperimento
        with open(file.replace('.npz',''), "r", encoding='utf-8') as file_desc:
            text = file_desc.read()
            print(text)
    except FileNotFoundError:
        print(f"Description of {file} not found.")
    # Caricamento dei dati
    data=np.load(file)
    try:
        if index == 0:
            V = data['voltage']
            R = data['resistance']
            T = data['temperature']
            I = data['current_source']
            J = data['current_density']
            E = data['electric_field']
            RHO = data['resistivity']
        else:
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

# answer = eg.choicebox('Select the plot', 'Plot', ["RHO vs Temperature", "RHO vs I"])

# Correnti in mA
J = J * 1000
I = I * 1000
unit_current = "mA"

fixedTemperature = np.max(T) - np.min(T) < 1
fixedCurrent = np.max(I) == np.min(I)

if not fixedTemperature and not fixedCurrent:
    indexes_max = np.where(I == np.max(I))[0]
    indexes_min = np.where(I == np.min(I))[0]
    # I grafici 2D sono visualizzati solo se sono individuati correttamente i cicli di corrente
    if len(indexes_min) == len(indexes_max):
        ## Grafici 2D
        fig, [ax, ax1] = plt.subplots(2,1)
        for i in range(len(indexes_min)):
            # Plot V vs I
            ax.plot(I[indexes_min[i]:indexes_max[i]], V[indexes_min[i]:indexes_max[i]], '.',
label=f'{round(np.average(T[indexes_min[i]:indexes_max[i]]))}')
            # Plot RHO vs J
            ax1.plot(J[indexes_min[i]:indexes_max[i]], RHO[indexes_min[i]:indexes_max[i]], '.',
label=f'{round(np.average(T[indexes_min[i]:indexes_max[i]]))}',)
     
        ax.set(xlabel=unit_current, ylabel='V', title="V vs I", yscale='linear')
        ax.grid()
        ax.legend(title="Temp (°K)")

        ax1.set(xlabel=unit_current+'/cm2', ylabel='Ohm cm', title="RHO vs J", yscale='linear', xscale='linear')
        ax1.grid()
        ax1.legend(title="Temp (°K)")

        fig, ax2 = plt.subplots()
        for j in range(0, indexes_max[0]+1, 10):
           # print(indexes_min + j, I[indexes_min + j])
            ax2.plot(T[indexes_min + j], RHO[indexes_min + j], '.-',
    label=f'{J[indexes_min + j][0]:.2f}',)

        ax2.set(xlabel='°K', ylabel='Ohm cm', title="RHO vs T", yscale='linear', xscale='linear')
        ax2.grid()
        ax2.legend(title="J ("+ unit_current +"/cm2)")

    ## Grafici 3D
    mappable = plt.cm.ScalarMappable(cmap=cm.turbo)
    mappable.set_array(T)

    fig3d_a = plt.figure()
    ax3d_a = plt.axes(projection='3d')
    fig3d_a.colorbar(mappable)

    fig3d_b = plt.figure()
    ax3d_b = plt.axes(projection='3d')
    fig3d_b.colorbar(mappable)

    fig3d_c = plt.figure()
    ax3d_c = plt.axes(projection='3d')
    fig3d_c.colorbar(mappable)
    try:
        ax3d_a.set(title="V vs I and Temperature", xlabel=unit_current, ylabel='V', zlabel='(°K)')
        ax3d_a.scatter(I, V, T, cmap=mappable.cmap, norm=mappable.norm, c=mappable.get_array())
        # Individuazione dei massimi e dei minimi
        v_min = np.argmin(V)
        v_max = np.argmax(V)
        ax3d_a.text(I[v_max], V[v_max], T[v_max], f"{V[v_max]:.2e}V", color='red')
        ax3d_a.text(I[v_min], V[v_min], T[v_min], f"{V[v_min]:.2e}V", color='orange')
        ax3d_b.set(title='E vs J and Temperature', xlabel=unit_current+'/cm2', ylabel='V cm', zlabel='(°K)')
        ax3d_b.scatter(J, E, T, cmap=mappable.cmap, norm=mappable.norm, c=mappable.get_array())

        # Individuazione dei massimi e dei minimi
        e_min = np.argmin(E)
        e_max = np.argmax(E)
        ax3d_b.text(J[e_max], E[e_max], T[e_max], f"{E[e_max]:.2e}V/cm", color='red')
        ax3d_b.text(J[e_min], E[e_min], T[e_min], f"{E[e_min]:.2e}V/cm", color='orange')

        ax3d_c.set(title='Rho vs J and Temperature', xlabel=unit_current +'/cm2', ylabel='Ohm cm', zlabel='(°K)')
        ax3d_c.scatter(J, RHO, T, cmap=mappable.cmap, norm=mappable.norm, c=mappable.get_array())
        # Individuazione dei massimi e dei minimi
        r_min = np.argmin(RHO)
        r_max = np.argmax(RHO)
        ax3d_c.text(J[r_max], RHO[r_max], T[r_max], f"{RHO[r_max]:.2e}Ohm/cm", color='red')
        ax3d_c.text(J[r_min], RHO[r_min], T[r_min], f"{RHO[r_min]:.2e}Ohm/cm", color='orange')
    except NameError:
        pass

## Grafici 2D a temperatura fissata
if fixedTemperature and not fixedCurrent:
    fig, [ax, ax1] = plt.subplots(2,1)
    try:
        ax.plot(I, V, ".-")
        # Annotate Start point
        # ax.plot(I[0], V[0], "o", color="green")
        ax.annotate("Start",
            xy=(I[0], V[0]), xycoords='data', color="green")

        # Annotate End point
        # ax.plot(I[-1], V[-1], "o", color="red")
        ax.annotate("End",
            xy=(I[-1], V[-1]), xycoords='data', color="red")
        ax.set(xlabel=unit_current, ylabel='V', title="V-I Characteristics") #, yscale='log', xscale='log')
        ax.grid()

        ax1.plot(J, RHO, ".-")
        # Annotate Start point
        # ax1.plot(J[0], RHO[0], "o", color="green")
        ax1.annotate("Start",
            xy=(J[0], RHO[0]), xycoords='data', color="green")

        # Annotate End point
        # ax1.plot(J[-1], RHO[-1], "o", color="red")
        ax1.annotate("End",
           xy=(J[-1], RHO[-1]), xycoords='data', color="red")
        ax1.set(xlabel=unit_current +'/cm2', ylabel='Ohm cm', title="Resistivity vs J")
        #, yscale='log', xscale='log')
        ax1.grid()
    except NameError:
        pass

if not fixedTemperature and fixedCurrent:
    fig, [ax, ax1] = plt.subplots(2,1)
    # Plot V vs T
    ax.plot(T, V, ".-")
    # Annotate Start point
    # ax.annotate("Start", xy=(T[0], V[0]), xycoords='data', color="green")

    # Annotate End point
    # ax.annotate("End", xy=(T[-1], V[-1]), xycoords='data', color="red")
    ax.set(xlabel='°K', ylabel='V', title="Voltage vs Temperature", yscale='log')
    ax.grid()

    # Plot RHO vs T
    ax1.plot(T, RHO, ".-")
    # Annotate Start point
    # ax1.annotate("Start", xy=(T[0], RHO[0]), xycoords='data', color="green")

    # Annotate End point
    # ax1.annotate("End", xy=(T[-1], RHO[-1]), xycoords='data', color="red")
    ax1.set(xlabel='°K', ylabel='Ohm cm', title="Resistivity vs Temperature", yscale='log')
    ax1.grid()

plt.show()
