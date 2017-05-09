

from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import fridge, res, heman, nwa
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\160603 - EonHe M016v5\data', today, "%s_helium_electrophoresis" % now)
    print "Saving data in %s" % expt_path
    if not os.path.isdir(expt_path):
        os.mkdir(expt_path)

    prefix = "helium_electrophoresis"
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

        Vres = res.get_volt()
        ehe.dataCache.post('Vres', Vres)

        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        #Vtrap = trap.get_volt()
        #ehe.dataCache.post('Vtrap', Vtrap)

        fpts, mags, phases = nwa.take_one_in_mag_phase(sweep_points)
        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('mags', mags)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('time', time() - ehe.t0)

        return temperature

    nwa.clear_traces()
    nwa.setup_measurement('S21')

    sweep_points = 401
    nwa.configure(center=5.65891e9,
                  span=6e6,
                  sweep_points=sweep_points,
                  power=-35,
                  averages=1,
                  ifbw=10e3)

    nwa.set_electrical_delay(68.414E-9)
    nwa.setup_take(averages_state=True)

    #n_points = 102
    dV = 0.050

    Vress = list(np.arange(0, +6, +dV)) \
            + list(np.arange(+6, -6, -dV)) \
            + list(np.arange(-6, 0, +dV))

    plt.subplot(211)
    plt.plot(Vress, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")
    # plt.show()

    fpts, mags, phases = nwa.take_one_in_mag_phase()

    plt.subplot(212)
    plt.plot(fpts, mags, color="#F0AD32", markeredgecolor="none")
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()

    #print "now unload previous experiment"
    #res.set_volt(-3)
    print "sleep for 5 seconds..."
    sleep(5)

    def print_trace():
        fpts, mags, phases = nwa.take_one_in_mag_phase()

        plt.figure()
        plt.plot(fpts, mags, color="#F0AD32", markeredgecolor="none")
        plt.show()

    #print_trace()

    ehe.dataCache.set('puff', 101)

    for Vres in tqdm(Vress):
        res.set_volt(Vres)
        #trap.set_volt(Vres)
        take_trace_and_save(sweep_points)


