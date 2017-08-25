#from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, heman, nwa, filament
from resonance_fitting import fit_res_gerwin
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0020_electron_loading_resonator_suck_E5071C.py"

#res = seekat
t0 = time()

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_electron_loading_resonator_suck" % now)
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


    def set_voltages(res, trap, res_guard, trap_guard, pinch=None, verbose=True):
        if res is not None:
            seekat.set_voltage(1, res, verbose=verbose)
        if trap is not None:
            seekat.set_voltage(2, trap, verbose=verbose)
        if res_guard is not None:
            seekat.set_voltage(3, res_guard, verbose=verbose)
        if trap_guard is not None:
            seekat.set_voltage(4, trap_guard, verbose=verbose)
        if pinch is not None:
            seekat.set_voltage(5, pinch, verbose=verbose)
        dataCache.post("voltage_log", np.array([time(),
                                                seekat.get_voltage(1), seekat.get_voltage(2),
                                                seekat.get_voltage(3), seekat.get_voltage(4),
                                                seekat.get_voltage(5)]))


    def get_voltages():
        return seekat.get_voltage(1), seekat.get_voltage(2), seekat.get_voltage(3), \
               seekat.get_voltage(4), seekat.get_voltage(5)

    filament.setup_driver(**filamentParams)
    filament.set_timeout(10000)
    print filament.get_id()

    def unload():
        print "********************"
        print "UNLOADING ELECTRONS!"
        print "********************"
        for k in range(5):
            print "\tStep %d"%(k+1)
            for volts in [-1, -2, -3, -4, -3, -2, -1]:
                set_voltages(volts, volts, volts, volts, verbose=False)
                sleep(0.5)

    def unload_trap(start=-3.0, stop=-5.0):
        print "********************"
        print "UNLOADING TRAP ONLY!"
        print "********************"
        res_init, trap_init, res_guard_init, trap_guard_init, pinch = get_voltages()
        vs = list(np.arange(start, stop, -1)) +\
             list(np.arange(stop, start, +1))
        for k in range(5):
            print "\tStep %d"%(k+1)
            for volts in vs:
                set_voltages(res_init, volts, res_guard_init, trap_guard_init, verbose=False)
                sleep(0.5)
        set_voltages(res_init, trap_init, res_guard_init, trap_guard_init)

    def take_trace_and_save(averages):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        Vres, Vtrap, Vrg, Vtg, Vpinch = get_voltages()
        dataCache.post('Vres', Vres)
        dataCache.post('Vtrap', Vtrap)
        dataCache.post('Vrg', Vrg)
        dataCache.post('Vtg', Vtg)
        dataCache.post('Vpinch', Vpinch)

        if averages > 1:
            fpts, mags, phases = nwa.take_one_averaged_trace()
        else:
            fpts, mags, phases = nwa.take_one()

        dataCache.post('fpts', fpts)
        dataCache.post('mags', mags)
        dataCache.post('phases', phases)
        dataCache.post('time', time() - t0)
        return temperature

    def unload_with_filament():
        # First loading to get rid of most electrons!
        if load_electrons:
            set_voltages(-3.0, -3.0, 0.0, 0.0)
            sleep(2.0)
            temperature = fridge.get_mc_temperature()
            print "Waiting for consistent electron loading temperature of < 550 mK...."
            while temperature > 0.550:
                temperature = fridge.get_mc_temperature()
                sleep(2)
                print '.',
            filament.fire_filament(100, 0.01)
            print "Fired filament!"
            sleep(60.0)

    def load_trap_not_resonator():
        print "\n"
        print "********************"
        print "LOADING ELECTRONS..."
        print "********************"
        set_voltages(-2.0, 3.0, 1.00, 1.00)
        sleep(2.0)
        temperature = fridge.get_mc_temperature()
        print "Waiting for consistent electron loading temperature of < 550 mK...."
        while temperature > 0.550:
            temperature = fridge.get_mc_temperature()
            sleep(2)
            print '.',
        filament.fire_filament(100, 0.01)
        print "Fired filament!"
        sleep(120.0)

        not_settled = True
        stable_temp = 0.550
        # print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
        while not_settled:
            temperature = fridge.get_mc_temperature()
            if temperature <= stable_temp:
                not_settled = False

    nwa.set_measure('S21')
    unload()

    load_electrons = True

    power = -40
    averages = 25
    sweep_points = 801

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    nwa_config = {'start' : 6.385E9,
                  'stop': 6.407E9,
                  'sweep_points': sweep_points,
                  'power': power,
                  'averages': averages,
                  'ifbw': nwa.get_ifbw()}

    nwa.configure(**nwa_config)
    nwa.set_electrical_delay(68E-9)
    nwa.set_phase_offset(180.0)
    dataCache.set_dict('nwa_config', nwa_config)
    nwa.auto_scale()

    Vressweep = list(np.arange(-2.0, 2.0, 0.025)) + list(np.arange(2.0, 0.0, -0.025))
    Vtraps = list(np.arange(3.0, 0.2, -0.05)) \
             + list(0.2*np.ones(len(Vressweep)))
    Vress = -2.0 * np.ones(len(Vtraps))
    Vress[-len(Vressweep):] = Vressweep
    Vresguards = 0.0 * np.ones(len(Vtraps))

    fig = plt.figure(figsize=(8.,12.))
    plt.subplot(311)
    plt.plot(Vress, 'o', color="#23aaff", markeredgecolor="none", label="Resonator")
    plt.plot(Vtraps, 'o', color="#f4b642", markeredgecolor="none", label='Trap')
    plt.plot(Vresguards, 'o', color="lawngreen", markeredgecolor="none", label='Res guard')
    plt.ylabel("Resonator voltage (V)")
    plt.xlim(0, np.max([len(Vress), len(Vtraps)]))
    plt.legend(loc=0, prop={'size' : 8})

    if averages > 1:
        fpts, mags, phases = nwa.take_one_averaged_trace()
    else:
        fpts, mags, phases = nwa.take_one()

    plt.subplot(312)
    current_vres, current_vtrap, current_vrg, current_vtg, pinch = get_voltages()
    plt.text(np.min(fpts) + 0.10*(np.max(fpts)-np.min(fpts)),
             np.min(mags) + 0.85*(np.max(mags) - np.min(mags)),
            "res, trap, rg, tg = (%.2fV, %.2fV, %.2fV, %.2fV)" % (current_vres, current_vtrap, current_vrg, current_vtg))
    plt.plot(fpts, mags)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (dB)')
    plt.xlim(np.min(fpts), np.max(fpts))

    plt.subplot(313)
    plt.plot(fpts, phases)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(fpts), np.max(fpts))

    fig.savefig(os.path.join(expt_path, "pre_electron_loading.png"), dpi=200)

    plt.show()

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    #unload_with_filament()

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')
    nwa.set_average_state(True)

    if load_electrons:
        abs_deltaf = 1e9
        Q = 0
        # Set both the Q and deltaf threshold to something low if you want it to continue after the first load
        while not (Q > 9000 and abs_deltaf > 0.0):
            unload_with_filament()
            load_trap_not_resonator()
            #set_voltages(0.6, -2.0, 0.0, 0.0)
            #set_voltages(Vress[0], Vtraps[0], None)
            if averages > 1:
                fpts, mags, phases = nwa.take_one_averaged_trace()
            else:
                fpts, mags, phases = nwa.take_one()
            f0, Q = fit_res_gerwin(fpts, mags, span=3E6)
            abs_deltaf = np.abs(f0-6.40511e9)
            print "Fit result after loading: delta f = %.2f MHz and Q = %.0f" % (abs_deltaf/1E6, Q)
        sleep(120)

    nwa.set_center_frequency(f0-0.25e6)
    nwa.set_span(1.0E6)
    print "Set center frequency to %.6f GHz (shift = %.2f MHz)"%(f0/1E9, (f0-6.40511e9)/1E6)

    set_voltages(None, None, 0.00, 0.00)
    print "Starting resV sweep..."
    set_voltages(Vress[0], Vtraps[0], Vresguards[0], None, -1.00)
    for Vres, Vtrap, Vresguard in tqdm(zip(Vress, Vtraps, Vresguards)):
        set_voltages(Vres, Vtrap, Vresguard, None)
        take_trace_and_save(averages)

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

