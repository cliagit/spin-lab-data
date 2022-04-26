#!/usr/bin/env python3

'''
 Electrical characteristic experiment with voltage source
 Keithely Source 2400 meter as fixed or variable voltage generator and
 current meter; Keithely multimeter 2000 or 2700 to measure temperature with silicon diode DT470
'''
from datetime import datetime
from time import sleep
from scipy import signal
import threading
import configparser
import sys
import os
import shutil
import logging
from matplotlib import pyplot as plt
from matplotlib import animation
import easygui as eg
import pandas as pd
import numpy as np
import gpib
import Gpib
from lib import DT400TempSensor as sensor

# Creazione del file di logging
logging.basicConfig(filename=sys.argv[0].replace('.py', '.log'),
                    format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', encoding='utf-8', level=logging.INFO)

# Stile della finestra dei grafici
plt.style.use('dark_background')

# Load configuration file
# Lettura del file .ini corrispondente
config = configparser.ConfigParser()
config.read(sys.argv[0].replace('.py', '.ini'))
conf = config['DEFAULT']

# Nome del campione in esame
SAMPLE_NAME = conf['SAMPLE_NAME']
# Dimensioni del campione
AREA = conf.getfloat('AREA')
LENGTH = conf.getfloat('LENGTH')
# Numero di valori sui quali fare la media
AVG_MEASURE = conf.getint('AVG_MEASURE')
# Source number of samples
SOURCE_SAMPLES = conf.getint('SOURCE_SAMPLES')
SOURCE_FLIPPED = conf.getboolean('SOURCE_FLIPPED')

# Misure in continuo
continuous_mode = conf.getboolean('CONTINUOUS_MODE')
# Numero di punti da visualizzare sul grafico
DISPLAY_SAMPLES = int(SOURCE_SAMPLES * 1.15)

# Select fixed or variable source
if conf.getboolean('SOURCE_FIXED'):
    SOURCE_FLIPPED = False
    # Fixed source
    SOURCE =  np.ones(SOURCE_SAMPLES) * conf.getfloat('SOURCE_FIXED_VALUE')
    title = f"{SAMPLE_NAME} at fixed voltage {conf['SOURCE_FIXED_VALUE']}V"
else:
    if conf.getboolean('SOURCE_SQUARE_WAVE'):
        SOURCE_FLIPPED = False
        SOURCE_SQUARE_VALUE = conf.getfloat('SOURCE_SQUARE_VALUE')
        SOURCE_SQUARE_PERIOD = conf.getint('SOURCE_SQUARE_PERIOD')
        t = np.linspace(0, 1, SOURCE_SAMPLES)
        SOURCE = signal.square(( 2 * np.pi * SOURCE_SQUARE_PERIOD *t )) * SOURCE_SQUARE_VALUE
        title = f"{SAMPLE_NAME} voltage square waveform value {SOURCE_SQUARE_VALUE}V"
    else:
        # Variable min source
        SOURCE_VAR_MIN_VALUE = conf.getfloat('SOURCE_VAR_MIN_VALUE')
        # Variable max source
        SOURCE_VAR_MAX_VALUE = conf.getfloat('SOURCE_VAR_MAX_VALUE')
        # Variable array of num sample from start to end equally spaced
        SOURCE = np.linspace(SOURCE_VAR_MIN_VALUE, SOURCE_VAR_MAX_VALUE, SOURCE_SAMPLES)
        title = f"{SAMPLE_NAME} voltage from {conf['SOURCE_VAR_MIN_VALUE']} to {conf['SOURCE_VAR_MAX_VALUE']}V"

# Append flipped current array of num sample from end to start
if SOURCE_FLIPPED:
    SOURCE = np.concatenate((SOURCE, np.flip(SOURCE)))
    DISPLAY_SAMPLES *= 2
    title += ' flipped'
    logging.info('Source is flipped')

logging.info('### Start experiment: %s ###', title)

# Intervallo di acquisizione
DELAY = conf.getfloat('DELAY')
# Inizializzazione del sensore di temperatura al silicio
dt400 = sensor.DT400TempSensor()

### Configurazione del multimetro Keithley 2700
# Port GPIB 0, GPIB Intrument address 16
try:
    multimeter=Gpib.Gpib(0,16)
    # Reset GPIB
    multimeter.write("*RST")
    # Identify request
    multimeter.write("*IDN?")
    # Read answer
    logging.info('Found Multimeter %s', multimeter.read().decode("utf-8"))
    # Select source function, mode Voltage reading only.
    multimeter.write(":SENS:FUNC 'VOLT'")
    # CHANNEL 1
    multimeter.write(":FORM:ELEM READ")
except gpib.GpibError as e:
    logging.fatal("Multimeter doesn't respond: %s", e)
    print("Multimeter doesn't respond, check it out!", e)
    sys.exit(-1)

### Configurazione del SourceMeter Keithley 2400
# Port GPIB 0, GPIB Intrument address 24
try:
    sm=Gpib.Gpib(0,24)
    # Reset GPIB defaults
    sm.write("*RST")
    # Identify request
    sm.write("*IDN?")
    # Read answer from device
    logging.info('Found Source Meter %s', sm.read().decode("utf-8"))
    # print(sm.read().decode('utf-8'))
### Select source function, mode '''
    #Select voltage source.
    sm.write(":SOUR:FUNC VOLT")
    # Source output.
    sm.write(f":SOUR:VOLT:LEV {SOURCE[0]}")
    # Current compliance.
    sm.write(f':SENS:CURR:PROT {conf["LIMIT"]}')
    # Current measure function.
    sm.write(":SENS:FUNC 'CURR'")
    # Current reading only.
    sm.write(":FORM:ELEM CURR")
    # Turn on source meter output
    sm.write(":OUTP ON")
except gpib.GpibError as e:
    logging.fatal("Source meter 2400 doesn't respond: %s", e)
    print("Source meter doesn't respond, check it out!", e)
    sys.exit(-1)

# Instantiate threading event handler
# Evento uscita dal ciclo di misura
exit_event = threading.Event()

def measure_thread_function():
    """ Measurement thread """
    global start_measurements
    start_measurements = False

    # Array of resistence values
    global R
    R = []
    # Array of temperature measures
    global T
    T = []
    # Array of datetime
    global DT
    DT = []
    # Array of voltage measures
    global V
    V = []
    # Array of current values
    global I
    I = []
    # Array of resistivity values
    global RHO
    RHO = []
    # Array of electric field values
    global E
    E = []
    # Array of current density values
    global J
    J = []
    if continuous_mode:
        eg.msgbox('Start new measurement loop in continuous mode; to stop and save the measurements close the plot \
window')
        logging.info("Start the measurement loop in continuous mode")
    else:
        logging.info("Start the measurement loop")
    # Measurement loop
    while True:
        try:
            # Impostazione del valore iniziale del voltaggio
            sm.write(f":SOUR:VOLT {SOURCE[0]}")
        except gpib.GpibError as e:
            logging.warning("Writing gpib error, check the source meter: %s", e)
            # print(f"Writing gpib error: {e}")

        # Thread exits, interruzione del ciclo di misura
        if exit_event.is_set():
            logging.info("End of the measurement loop")
            break
        if not continuous_mode:
            answer = 'temperature'
            while 'temperature' in answer:
                try:
                    # Read temperature
                    multimeter.write(':READ?')
                    tmp= dt400.voltage_to_temp(float(multimeter.read()))
                except gpib.GpibError as e:
                    logging.warning("Reading gpib error, check the multimeter: %s", e)
                    # print(f"Reading error, check the instruments: {e}")
                start_measurements = False
                # Dialogo per l'avvio del ciclo di corrente
                answer = eg.buttonbox(f'Start new measurement loop at the current temperature: \
    {tmp:.2f}? If you answer No, close the plot window to save the experiment',\
    'Measurement loop', ('Yes, go on', 'Show me the temperature' ,'No, I have done'))
            if not answer == 'Yes, go on':
                break
        start_measurements = True
        # Ciclo della voltaggio
        for volt in SOURCE:
            try:
                # Thread exits, interruzione del ciclo di misura
                if exit_event.is_set():
                    logging.info("Leaving the measurement loop")
                    break

                # Impostazione del voltaggio
                sm.write(f":SOUR:VOLT {volt}")
                logging.info("Measurement at voltage %s", volt)
                error = False
                curr_sum = 0.0
                temp_sum = 0.0
            except gpib.GpibError as e:
                logging.warning("Writing gpib error, check the source meter: %s", e)
                # print(f"Writing gpib error: {e}")

            # Ciclo su n misure
            for _j in range(AVG_MEASURE):
                # print(f"\nMisura :{_j}\n")
                try:
                    # Read current
                    sm.write(':READ?')
                    curr_measure = float(sm.read())
                    curr_sum += curr_measure
                    sleep(DELAY)
                    # Read temperature
                    multimeter.write(':READ?')
                    temp_measure = dt400.voltage_to_temp(float(multimeter.read()))
                    temp_sum += temp_measure
                    sleep(DELAY)
                    error = False
                except ValueError:
                    error = True
                    logging.warning('Temperature out of range!')
                    # print("Temperature out of range!")
                    break
                except gpib.GpibError as e:
                    error = True
                    logging.warning("Reading gpib error, check the instruments: %s", e)
                    # print(f"Reading error, check the instruments: {e}")
                    break
            if not error:
                temp = temp_sum/AVG_MEASURE
                curr = curr_sum/AVG_MEASURE
                res = volt/curr
                e_field = volt/LENGTH
                c_density = curr/AREA
                rho = e_field/c_density
                log_measure = f'T:{temp:.2f}°K V:{volt:.4e}V I:{curr:.4e}A R:{res:.4e}𝛀 \
E:{e_field:.4e}V/cm J:{c_density:.4e}A/cm2 𝛒:{rho:.4e}𝛀 cm'
                # print(f'T:{temp:.2f}°K V:{volt:.4e}V I:{i:.4e}A R:{res:.4e}𝛀 \
#E:{e_field:.4e}V/cm J:{c_density:.4e}A/cm2 𝛒:{rho:.4e}𝛀 cm',
#                end="\r")
                logging.info('%s', log_measure)
                if curr >= float(conf["LIMIT"]) - 0.1:
                    logging.warning("Current compliance")
                else:
                    # Update current array
                    I.append(curr)
                    # Update voltage array
                    V.append(volt)
                    # Update resistance array
                    R.append(res)
                    # Update temperature array
                    T.append(temp)
                    # Update datetime array
                    DT.append(datetime.now())
                    # Derivazione degli altri parametri
                    # Campo elettrico
                    E.append(e_field)
                    # Densità di corrente
                    J.append(c_density)
                    # Resistività
                    RHO.append(rho)

# Configure and Start Measurement thread loop
thr_measure = threading.Thread(target=measure_thread_function)
thr_measure.start()

### Plotting ###
fig, [ax0, ax1, ax2] = plt.subplots(3,1, figsize=(16, 12))
ax0.set(ylabel='Resistance [Ohm]', xlabel='Time', title=title)
ax1.set(ylabel='Current [A]', xlabel='Time')# , yscale='log', xscale='log')
ax2.set(ylabel='Temperature [°K]', xlabel='Time') # , yscale='log', xscale='log')

ax0.grid()
ax1.grid()
ax2.grid()

# Lista delle annotazioni
ann_list = []

def update_plot(i):
    """ animation function.  This is called sequentially """
   # print(i, T[i], R[i])
    N = len(DT)
    if not start_measurements:
        try:
            # Read temperature
            multimeter.write(':READ?')
            tmp= dt400.voltage_to_temp(float(multimeter.read()))
            print(f'Current Temperature:{tmp:.2f}°K', end='\r')
        except gpib.GpibError as e:
            logging.warning("Reading gpib error, check the multimeter: %s", e)
        except ValueError:
            logging.warning('Temperature out of range!')

    else:
        if N > DISPLAY_SAMPLES:
            ax0.cla()
            ax0.grid()
            ax1.cla()
            ax1.grid()
            ax2.cla()
            ax2.grid()
            ax0.set(ylabel='Resistance [Ohm]', xlabel='Time', title=title)
            ax1.set(ylabel='Current [A]', xlabel='Time')# , yscale='log', xscale='log')
            ax2.set(ylabel='Temperature [°K]', xlabel='Time') # , yscale='log', xscale='log')
            #ax0.set_xlim([DT[N - DISPLAY_SAMPLES], DT[N-1]])
            #ax1.set_xlim([DT[N - DISPLAY_SAMPLES], DT[N-1]])
            #ax2.set_xlim([DT[N - DISPLAY_SAMPLES], DT[N-1]])
            ax0.plot(DT[N - DISPLAY_SAMPLES:-1], R[N - DISPLAY_SAMPLES:-1], '.-', color='orange')
            ax1.plot(DT[N - DISPLAY_SAMPLES:-1], I[N - DISPLAY_SAMPLES:-1], '.-', color='red')
            ax2.plot(DT[N - DISPLAY_SAMPLES:-1], T[N - DISPLAY_SAMPLES:-1], '.-', color='yellow')
        else:
            ax0.plot(DT[:i], R[:i], '.-', color='orange')
            ax1.plot(DT[:i], I[:i], '.-', color='red')
            ax2.plot(DT[:i], T[:i], '.-', color='yellow')

        if N > 0:
            # Rimozione delle annotazioni precedenti
            for _k, ann_item in enumerate(ann_list):
                ann_item.remove()
            ann_list[:] = []
            ## Annotazioni riportanti gli ultimi valori misurati
            # Resistenza
            an0 = ax0.annotate(f'{R[-1]:.3e}', xy=(1.01, 0.9),  xycoords='axes fraction', color="w")
            # Voltaggio
            an1 = ax1.annotate(f'{I[-1]:.3e}', xy=(1.01, 0.9),  xycoords='axes fraction', color="w")
            # Temperatura
            an2 = ax2.annotate(f'{T[-1]:.2e}', xy=(1.01, 0.9),  xycoords='axes fraction', color="w")
            ann_list.append(an0)
            ann_list.append(an1)
            ann_list.append(an2)

def on_close(event):
    """ On close plotting window event handler """
    # Trigger measurement thread exit event
    exit_event.set()
    thr_measure.join()
    date_time = datetime.now().strftime("%Y%m%d%H%M%S")
    answer = eg.ynbox('Save data?', 'Closing the experiment', ('Yes', 'No'))
    if answer and len(T) > 0:
        path = SAMPLE_NAME + "/" + title.replace(" ", "_")
        path_file = path + "/" + title.replace(" ", "_") + "-" + date_time
        try:
            # Creazione, se non esistente, della cartella base col nome del campione
            if not os.path.exists(SAMPLE_NAME):
                os.mkdir(SAMPLE_NAME)
            # Creazione, se non esistente, della cartella dell'esperimento
            if not os.path.exists(path):
                os.mkdir(path)
            # Create and save README file descriptor
            logging.info("Save the description file")
            with open(path_file, "a", encoding='utf-8') as file:
                file.write(conf['DESCRIPTION'])
                file.write(f"\nName of the sample: {SAMPLE_NAME}")
                file.write(f"\nArea: {conf['AREA']}cm2")
                file.write(f"\nLength: {conf['LENGTH']}cm")
                if conf.getboolean('SOURCE_FIXED'):
                    file.write(f"\nVoltage source fixed at {conf['SOURCE_FIXED_VALUE']}V")
                elif conf.getboolean('SOURCE_SQUARE_WAVE'):
                   file.write(f"\nVoltage square waveform source, value {conf['SOURCE_SQUARE_VALUE']}V")
                elif SOURCE_FLIPPED:
                    file.write(f"\nVoltage source starts and ends at {conf['SOURCE_VAR_MIN_VALUE']}V \
through {conf['SOURCE_VAR_MAX_VALUE']}V")
                else:
                    file.write(f"\nVoltage source from {conf['SOURCE_VAR_MIN_VALUE']}V to \
{conf['SOURCE_VAR_MAX_VALUE']}V")
                file.write(f'\n\n### Experiment {date_time} ###')
                file.write(f'\nDate {DT[0].strftime("%Y-%m-%d")} start at \
{DT[0].strftime("%H:%M:%S")} end at {DT[-1].strftime("%H:%M:%S")} \
duration {str(DT[-1].replace(microsecond=0)-DT[0].replace(microsecond=0))}')
                file.write(f'\nTemperature range from {T[0]:.2f}°K to {T[-1]:.2f}°K')
                file.write('\nResistivity:')
                file.write(f'\n\t average {np.average(RHO):.4e}𝛀 cm')
                file.write(f'\n\t minimum {np.min(RHO):.4e}𝛀 cm at {T[np.argmin(R)]:.2f}°K')
                file.write(f'\n\t maximum {np.max(RHO):.4e}𝛀 cm at {T[np.argmax(R)]:.2f}°K')
                file.write('\nCurrent:')
                file.write(f'\n\t average {np.average(I):.4e}A')
                file.write(f'\n\t minimum {np.min(I):.4e}A at {T[np.argmin(I)]:.2f}°K')
                file.write(f'\n\t maximum {np.max(I):.4e}A at {T[np.argmax(I)]:.2f}°K')
        except OSError as error:
            logging.error("Error handling description file: %s", error)
            # print(error)

        # Salvataggio dati formato numpy
        logging.info("Save data in numpy format %s", path_file)
        np.savez_compressed(path_file, datetime=DT, temperature=T,
                            voltage=V, resistance=R, current_source=I,
                            electric_field=E, current_density=J,
                            resistivity=RHO)

        # Salvataggio dati formato csv
        csv_path = path_file + ".csv"
        logging.info("Save data in CSV format %s", csv_path)
        data = pd.DataFrame(np.stack((T, V, R, I, E, RHO, J), axis=-1),
               columns=['Temperature [K]', 'Voltage source [V]', 'Resistance [𝛀]', 'Current [A]', \
'Electric Field [V/cm]', 'Restivity [𝛀 cm]', 'Current Density [A/cm2]'])
        data.to_csv(csv_path, index=False)

        # Salvataggio grafico
        fig_file = path_file + ".png"
        logging.info("Save plot as image %s", fig_file)
        fig.savefig(fig_file)
    else:
        logging.info("Data not saved")
        if len(T) <= 0:
            logging.warning("Data empty")
    answer1 = eg.ynbox('Switch off the Source Meter?', 'Closing the experiment', ('Yes', 'No'))
    if answer1:
        try:
            # Turn off source meter output
            sm.write(':OUTP OFF')
        except gpib.GpibError:
            logging.warning("Couldn't turn off the Source Meter")
            sys.exit(-1)
    if answer and len(T) > 0:
        # Copia del log
        shutil.copy(sys.argv[0].replace('.py', '.log'), path_file + ".log")
    logging.info("Closing the experiment")
    sys.exit(0)

anim = animation.FuncAnimation(plt.gcf(), update_plot, interval=500, blit=False)

# Impostazione dell'evento della chiusura della finestra
fig.canvas.mpl_connect('close_event', on_close)

plt.show()
