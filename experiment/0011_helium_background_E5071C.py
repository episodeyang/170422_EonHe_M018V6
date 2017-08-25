# -*- coding: utf-8 -*-

from slab.instruments.nwa import E5071
#from slab.instruments.Seekat import Seekat
from data_cache import dataCacheProxy
from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import fridge, heman, nwa, seekat
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os

res = seekat#Seekat.Seekat(address="COM11")

def calibrate_electrical_delay(init_delay):
    """
    Calibrate the electrical delay for the phase plot such that the
    slope present in the phase plot is zero.
    :param init_delay: Initial guess of the delay. Has to be reasonably close (unit: seconds)
    :return:
    """
    d1 = init_delay
    nwa.set_electrical_delay(d1)
    fpts, mags, phases = nwa.take_one()
    slope1 = np.mean(phases[-10:])-np.mean(phases[:10])

    d2 = d1 + 1E-9
    nwa.set_electrical_delay(d2)
    fpts, mags, phases = nwa.take_one()
    slope2 = np.mean(phases[-10:])-np.mean(phases[:10])

    return abs((d2*slope1 - d1*slope2)/(slope1 - slope2))

t0 = time()

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_helium_electrophoresis" % now)
    print "Saving data in %s" % expt_path
    if not os.path.isdir(expt_path):
        os.makedirs(expt_path)

    prefix = "helium_electrophoresis"
    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    #ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=True)
    dataCache = dataCacheProxy(file_path=os.path.join(expt_path, os.path.split(expt_path)[1] + ".h5"))


    def take_trace_and_save(sweep_points):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        Vres = res.get_voltage(1)
        dataCache.post('Vres', Vres)

        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        #Vtrap = trap.get_volt()
        #ehe.dataCache.post('Vtrap', Vtrap)

        fpts, mags, phases = nwa.take_one()
        dataCache.post('fpts', fpts)
        dataCache.post('mags', mags)
        dataCache.post('phases', phases)
        dataCache.post('time', time() - t0)

        return temperature

    nwa.set_measure('S21')

    averages = 1
    sweep_points = 1601

    nwa_config = {'center' : nwa.get_center_frequency(),
                  'span' : nwa.get_span(),
                  'sweep_points' : sweep_points,
                  'power' : nwa.get_power(),
                  'averages' : averages,
                  'ifbw' : nwa.get_ifbw()}

    nwa.configure(**nwa_config)
    dataCache.set_dict('nwa_config', nwa_config)

    #correct_delay = calibrate_electrical_delay(68E-9)
    #print correct_delay
    nwa.set_trigger_source('BUS')
    nwa.set_electrical_delay(68E-9)
    nwa.set_format('SLOG')
    nwa.auto_scale()

    dV = 0.005

    Vress = list(np.arange(0, +5, +dV)) \
            + list(np.arange(+5, 0, -dV))

    res.set_voltage(1, Vress[0])

    plt.figure(figsize=(8.,12.))
    plt.subplot(311)
    plt.plot(Vress, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")

    fpts, mags, phases = nwa.take_one()

    plt.subplot(312)
    plt.plot(fpts, mags)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))

    plt.subplot(313)
    plt.plot(fpts, phases)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()


    #print "now unload previous experiment"
    #res.set_volt(-3)
    print "sleep for 5 seconds..."
    sleep(5)

    #ehe.dataCache.set('puff', 90)

    for Vres in tqdm(Vress):
        res.set_voltage(1, Vres)
        take_trace_and_save(sweep_points)


