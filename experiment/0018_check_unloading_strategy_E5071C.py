from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, heman, nwa, filament
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0018_check_unloading_strategy_E5071C.py"

#res = seekat
t0 = time()

def set_voltages(res, trap, verbose=True):
    seekat.set_voltage(1, res, verbose=verbose)
    seekat.set_voltage(2, trap, verbose=verbose)

def get_voltages():
    return seekat.get_voltage(1), seekat.get_voltage(2)

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
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_check_unloading_500mK" % now)
    print "Saving data in %s" % expt_path

    if not os.path.isdir(expt_path):
        os.makedirs(expt_path)
    sleep(1)

    copyfile(os.path.join(r"S:\_Data\170422 - EonHe M018V6 with L3 etch\experiment", this_script),
             os.path.join(expt_path, this_script))

    dataCache = dataCacheProxy(file_path=os.path.join(expt_path, os.path.split(expt_path)[1] + ".h5"))

    prefix = "electron_loading"
    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    filamentParams = {"amplitude": 4.2,
                      "offset": -0.5,
                      "frequency": 113e3,
                      "duration": 40e-3}

    pulseParams = {"delay": .00,
                   "pulses": 200}

    # filament = FilamentDriver(address="192.168.14.144")
    filament.setup_driver(**filamentParams)
    filament.set_timeout(10000)
    print filament.get_id()

    # ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=True)
    # print ehe.filename

    # ehe.sample = lambda: None
    # ehe.sample.freqNoE = 6.16562e9
    # ehe.sample.freqWithE = 8023438335.47

    def unload():
        print "********************"
        print "UNLOADING ELECTRONS!"
        print "********************"
        t1=time()
        nwa.set_format('MLOG')
        nwa.set_trigger_source('INT')
        nwa.set_trigger_continuous(True)
        init_power = nwa.get_power()
        Vres_init, Vtrap_init = get_voltages()
        set_voltages(0.4, 0.4)
        nwa.set_power(+5)
        sleep(2.0)
        nwa.set_power(init_power)
        set_voltages(Vres_init, Vtrap_init)
        nwa.set_trigger_source('BUS')
        print "This took %.2f seconds"%(time()-t1)
        sleep(2.0)
        nwa.set_format('SLOG')

    def take_trace_and_save(averages):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        Vres, Vtrap = get_voltages() #res.get_voltage(1.0)
        dataCache.post('Vres', Vres)
        dataCache.post('Vtrap', Vtrap)
        dataCache.post('Vguards', seekat.get_voltage(3))

        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        #Vtrap = trap.get_volt()
        #ehe.dataCache.post('Vtrap', Vtrap)

        if averages > 1:
            fpts, mags, phases = nwa.take_one_averaged_trace()
        else:
            fpts, mags, phases = nwa.take_one()

        dataCache.post('fpts', fpts)
        dataCache.post('mags', mags)
        dataCache.post('phases', phases)
        dataCache.post('time', time() - t0)

        return temperature

    def check_loading(V1=3.0, V2=0.6, threshold=5, averages=1):
        fig = plt.figure()
        set_voltages(V1, V1)
        if averages > 1:
            fpts, mags, phases = nwa.take_one_averaged_trace()
        else:
            fpts, mags, phases = nwa.take_one()
        plt.plot(fpts, mags, label='%.2fV' % V1)
        max_idx = np.argmax(mags)
        initial_f0 = fpts[max_idx]
        transmission_i = mags[max_idx]
        set_voltages(V2, V2)
        sleep(1)
        if averages > 1:
            fpts, mags, phases = nwa.take_one_averaged_trace()
        else:
            fpts, mags, phases = nwa.take_one()
        plt.plot(fpts, mags, label='%.2fV' % V2)
        final_f0 = fpts[np.argmax(mags)]
        transmission_f = mags[max_idx]
        set_voltages(V1, V1)
        sleep(1)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Transmission")
        plt.ylim(-80, -30)
        plt.xlim(np.min(fpts), np.max(fpts))
        plt.legend(edgecolor='none', framealpha=1, loc=0, prop={"size": 10})

        fname = os.path.join(expt_path, "Check_Loading_001.png")
        idx = 1
        while os.path.isfile(fname):
            idx += 1
            fname = os.path.join(expt_path, "Check_Loading_%03d.png"%idx)


        fig.savefig(fname, dpi=200)
        plt.show()
        plt.close('all')

        if np.abs(transmission_f - transmission_i) > threshold:  # np.abs(final_f0 - initial_f0) > threshold:
            print "Electrons seem present"
            return True
        else:
            print "Shift too low! Measured shift was roughly %.2f kHz" % ((final_f0 - initial_f0) / 1E3)
            return False

    nwa.set_measure('S21')
    # Note unloading electrons here!
    #unload()

    load_electrons = True

    power = -30
    averages = 1
    sweep_points = 801

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    nwa_config = {'start' : 6.39E9,
                  'stop': 6.407E9,
                  'sweep_points': sweep_points,
                  'power': power,
                  'averages': averages,
                  'ifbw': nwa.get_ifbw()}

    nwa.configure(**nwa_config)
    dataCache.set_dict('nwa_config', nwa_config)
    nwa.auto_scale()

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    print "\n"
    print "********************"
    print "LOADING ELECTRONS..."
    print "********************"
    if load_electrons:
        set_voltages(3.0, -2.0)
        sleep(2.0)
        temperature = fridge.get_mc_temperature()
        print "Waiting for consistent electron loading temperature of < 50 mK...."
        while temperature > 0.550:
            temperature = fridge.get_mc_temperature()
            sleep(2)
            print '.',
        filament.fire_filament(100, 0.01)
        print "Fired filament!"
        sleep(10.0)

    not_settled = True
    stable_temp = 0.550
    print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
    while not_settled:
        temperature = fridge.get_mc_temperature()
        if temperature <= stable_temp:
            not_settled = False

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')
    nwa.set_average_state(True)

    # Set voltages for other electrodes:
    #res.set_voltage(2, 0.0) # DC bias pinch
    #res.set_voltage(3, 0.0) # Resonator guard

    #set_voltages(Vress[0], Vtraps[0])
    # if averages > 1:
    #     fpts, mags, phases = nwa.take_one_averaged_trace()
    # else:
    #     fpts, mags, phases = nwa.take_one()
    #
    # center_frequency = fpts[np.argmax(mags)]
    # span = 3E6
    # nwa.set_center_frequency(center_frequency)
    # nwa.set_span(span)
    # print "Set center frequency to %.6f GHz"%(center_frequency/1E9)

    seekat.set_voltage(3, +0.0)
    print "Starting resV sweep..."

    V1 = 3.0; V2=0.4;
    for k in range(3):
        check_loading(V1=V1, V2=V2, averages=averages)
        # Record traces for the data file
        #set_voltages(V1, V1)
        #take_trace_and_save(averages)
        #set_voltages(V2, V2)
        #take_trace_and_save(averages)
        # Now unload the electrons (or try to, at least)
        unload()
        print nwa.get_power()



