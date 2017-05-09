# -*- coding: utf-8 -*-
"""
Created on Mon Feb 06 22:13:59 2012

@author: Ge Yang
"""

from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import fridge, nwa
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os

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


if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_power_sweep" % now)
    print "Saving data in %s" % expt_path
    if not os.path.isdir(expt_path):
        os.mkdir(expt_path)

    prefix = "power_sweep"
    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=True)
    print ehe.filename

    ehe.sample = lambda: None
    ehe.sample.freqNoE = 6.16562e9
    ehe.sample.freqWithE = 8023438335.47

    def take_trace_and_save(sweep_points):
        temperature = fridge.get_mc_temperature()
        ehe.dataCache.post('temperature', temperature)

        #Vres = res.get_volt()
        #ehe.dataCache.post('Vres', Vres)

        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        #Vtrap = trap.get_volt()
        #ehe.dataCache.post('Vtrap', Vtrap)

        fpts, mags, phases = nwa.take_one()
        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('mags', mags)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('time', time() - ehe.t0)
        ehe.dataCache.post('powers', nwa.get_power())


        return temperature

    nwa.set_measure('S21')
    nwa.clear_averages()
    nwa.set_timeout(100000)

    averages = 5
    sweep_points = 1601
    powers = np.linspace(-40, 0, 21)

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=nwa.get_power(),
                  averages=averages,
                  ifbw=nwa.get_ifbw())

    #correct_delay = calibrate_electrical_delay(68E-9)
    #print correct_delay
    nwa.set_trigger_source('BUS')
    nwa.set_electrical_delay(64E-9)
    nwa.set_format('SLOG')
    nwa.auto_scale()
    nwa.set_average_state(True)
    nwa.set_trigger_average_mode(True)

    fpts, mags, phases = nwa.take_one()

    plt.figure(figsize=(8.,10.))
    plt.subplot(211)
    plt.plot(fpts, mags)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))

    plt.subplot(212)
    plt.plot(fpts, phases)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()


    #print "now unload previous experiment"
    #res.set_volt(-3)
    print "sleep for 5 seconds..."
    sleep(5)

    ehe.dataCache.set('puff', 90)

    for P in tqdm(powers):
        nwa.set_power(P)
        take_trace_and_save(sweep_points)

    nwa.set_power(powers[0])

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')
