# -*- coding: utf-8 -*-

import slab, os
#import util as util
from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from matplotlib import pyplot as plt
import numpy as np

from setup_instruments import heman, fridge, nwa
#from experiment.instruments import heman, fridge, nwa

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
    expt_path = os.path.join(r'S:\_Data\160603 - EonHe M016v5\data', today, "%s_monitor_peak_over_time"%now)
    print "Saving data in %s"%expt_path
    if not os.path.isdir(expt_path):
        os.mkdir(expt_path)
    
    prefix = "monitor_peak_over_time"
    fridgeParams = {
        'wait_for_temp': 0.080,
        'min_temp_wait_time': 60  # 11 minutes
    }

    ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=False)
    print ehe.filename

    ehe.note('Start experiment')

    ehe.sample = lambda: None
    ehe.sample.freqNoE = 6.16562e9
    ehe.sample.freqWithE = 8023438335.47

    nwa.set_measure('S21')
    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    averages = 1
    sweep_points = 401

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=nwa.get_power(),
                  averages=averages,
                  ifbw=nwa.get_ifbw())


    correct_delay = calibrate_electrical_delay(68E-9)
    print correct_delay
    nwa.set_electrical_delay(correct_delay)
    #nwa.set_format('SLOG')
    nwa.auto_scale()

    heman.seal_manifold()
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

    while True:
        temperature = fridge.get_mc_temperature()
        print time()
        fpts, mags, phases = nwa.take_one()

        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('mags', mags)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('temperature', temperature)
        ehe.dataCache.post('time', time())

        sleep(5)
