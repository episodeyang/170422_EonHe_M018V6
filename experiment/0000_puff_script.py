
import slab, os
#import util as util
#from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from matplotlib import pyplot as plt
import numpy as np

from setup_instruments import heman, fridge, nwa
from data_cache import dataCacheProxy as dataCache
#from experiment.instruments import heman, fridge, nwa

t0 = time()

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_helium_curve"%now)
    print "Saving data in %s"%expt_path
    if not os.path.isdir(expt_path):
        os.makedirs(expt_path)
    
    prefix = "helium_curve"
    fridgeParams = {
        'wait_for_temp': 0.080,
        'min_temp_wait_time': 60  # 11 minutes
    }

    #ehe = eHeExperiment(expt_path, prefix, fridgeParams)
    #print ehe.filename

    #ehe.note('start experiment. ')
    #ehe.note('putting puffs into the sample box')

    #ehe.sample = lambda: None
    f0 = 6.441e9
    #ehe.sample.freqWithE = 8023438335.47

    def take_trace_and_save(sweep_points):
        n = heman.get_puffs()
        dataCache.post('puff', n)

        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        fpts, mags, phases = nwa.take_in_mag_phase(sweep_points)
        # ehe.plotter.append_z('na spectrum', mags)
        dataCache.set('fpts', fpts)
        dataCache.post('mags', mags)
        dataCache.post('phases', phases)
        dataCache.post('time', time() - t0)

        return fpts, mags, phases
        #offset, amplitude, center, hwhm = dsfit.fitlor(fpts, dBmtoW(mags))
        #ehe.dataCache.post('f0', offset)
        #ehe.dataCache.post('hwhm', hwhm)

    nwa.clear_traces()
    nwa.setup_measurement('S21')

    sweep_points = 1601
    averages = 1
    average_state = True if averages > 1 else False
    nwa.set_start_frequency(f0 - 40E6)
    nwa.set_stop_frequency(f0 + 5E6)
    #nwa.set_center_frequency(5.672E9 - 5E6)
    nwa.set_sweep_points(sweep_points)
    #nwa.set_span(30e6)
    nwa.set_power(-25)
    nwa.set_ifbw(20e3)
    nwa.set_electrical_delay(68E-9)


    nwa.setup_take(averages=averages, averages_state=average_state)

    nwa.auto_scale()
    print "now take some trace"

    heman.seal_manifold()
    fpts, mags, phases = take_trace_and_save(sweep_points)
    plt.figure(figsize=(8.,10.))
    plt.subplot(211)
    plt.plot(fpts, mags)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))

    plt.subplot(212)
    plt.plot(fpts, phases*180/np.pi)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()

    print "Done!"
    #heman.set_puffs(60)
    #heman.clean_manifold(3)

    print 'start puffing'
    while heman.get_puffs() < 100:  # Fill in the number to which you want to fill.
       # ehe.note("Puff %d" % (heman.get_puffs() + 1))
        heman.puff(pressure=0.25, min_time=20, timeout=600)

        print "Wait for cooldown"
        settled = False
        start_time = time()

        while not settled:
            temperature = fridge.get_mc_temperature()
            print "temperature is", [temperature]
            settled = (temperature < 0.400) and ((time() - start_time) > 10.0)
            fpts, mags, phases = take_trace_and_save(sweep_points)
