#from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from slab.instruments import Triton, N5242A

fridge = Triton(address="192.168.14.129")
nwa = N5242A(address="192.168.14.221")

t0 = time()

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_power_sweep_full_range" % now)
    print "Saving data in %s" % expt_path
    if not os.path.isdir(expt_path):
        os.makedirs(expt_path)

    prefix = ""
    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    sleep(1)
    dataCache = dataCacheProxy(file_path=os.path.join(expt_path, os.path.split(expt_path)[1]+".h5"))

    # ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=True)
    # print ehe.filename

    def take_trace_and_save(sweep_points):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        fpts, mags, phases = nwa.take_one_in_mag_phase(sweep_points)
        dataCache.post('power', nwa.get_power())
        dataCache.post('fpts', fpts)
        dataCache.post('mags', mags)
        dataCache.post('phases', phases)
        dataCache.post('time', time() - t0)
        return temperature

    nwa.clear_traces()
    nwa.setup_measurement('S21')

    sweep_points = 401
    powers = np.arange(-80, +20, +5)
    p0 = -40 # power at which a single trace gives good enough SNR
    averages = 10**((p0 - powers)/10.) #* np.log10(p0 - powers)
    averages[averages > 500] = 500
    averages[averages <= 1] = 1
    averages[np.isnan(averages)] = 1

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=-powers[0],
                  averages=averages[0],
                  ifbw=1e3)

    nwa.set_electrical_delay(68)
    nwa.setup_take(averages_state=True)

    # fpts, mags, phases = nwa.take_one_in_mag_phase()
    #
    # plt.figure()
    # plt.plot(fpts/1E9, 20*np.log10(mags), color="#F0AD32", markeredgecolor="none")
    # plt.xlabel('Frequency (Hz)')
    # plt.ylabel('Magnitude (dB)')
    # plt.xlim(np.min(fpts)/1E9, np.max(fpts)/1E9)
    # plt.show()

    def print_trace():
        fpts, mags, phases = nwa.take_one_in_mag_phase()

        plt.figure()
        plt.plot(fpts, mags, color="#F0AD32", markeredgecolor="none")
        plt.show()

    for a, p in tqdm(zip(averages, powers)):
        print p, a
        nwa.setup_take(averages=a, averages_state=True)
        nwa.configure(center=nwa.get_center_frequency(),
                      span=nwa.get_span(),
                      sweep_points=sweep_points,
                      power=p,
                      averages=a,
                      ifbw=1e3)

        take_trace_and_save(sweep_points)

    nwa.set_power(p0)
    nwa.set_averages(1)




