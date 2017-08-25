#from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, yoko, nwa, filament
from resonance_fitting import fit_res_gerwin
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0017_electron_loading_res_trap_asymmetry_E5071C.py"

#res = seekat
t0 = time()

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_electron_loading_isolated_trap" % now)
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

    yoko.set_mode('VOLT')
    yoko.set_voltage_limit(10)
    yoko.set_output(True)

    def set_voltages(res, trap, res_guard, trap_guard, pinch=None, verbose=True):
        if res is not None:
            seekat.set_voltage(1, res, verbose=verbose)
        if trap is not None:
            yoko.set_volt(trap)
            #seekat.set_voltage(2, trap, verbose=verbose)
        if res_guard is not None:
            seekat.set_voltage(3, res_guard, verbose=verbose)
        if trap_guard is not None:
            seekat.set_voltage(4, trap_guard, verbose=verbose)
        if pinch is not None:
            seekat.set_voltage(5, pinch, verbose=verbose)
        # dataCache.post("voltage_log", np.array([time(),
        #                                         seekat.get_voltage(1), seekat.get_voltage(2),
        #                                         seekat.get_voltage(3), seekat.get_voltage(4),
        #                                         seekat.get_voltage(5)]))

        dataCache.post("voltage_log", np.array([time(),
                                                seekat.get_voltage(1), yoko.get_volt(),
                                                seekat.get_voltage(3), seekat.get_voltage(4),
                                                seekat.get_voltage(5)]))

    def get_voltages():
        # return seekat.get_voltage(1), seekat.get_voltage(2), seekat.get_voltage(3), \
        #        seekat.get_voltage(4), seekat.get_voltage(5)
        return seekat.get_voltage(1), yoko.get_volt(), seekat.get_voltage(3), \
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
            sleep(120.0)

    def load_resonator_not_trap():
        print "\n"
        print "********************"
        print "LOADING ELECTRONS..."
        print "********************"
        set_voltages(2.0, -3.0, 0.0, 0.0)
        sleep(2.0)
        temperature = fridge.get_mc_temperature()
        print "Waiting for consistent electron loading temperature of < 550 mK...."
        while temperature > 0.550:
            temperature = fridge.get_mc_temperature()
            sleep(2)
            print '.',
        filament.fire_filament(55, 0.01)
        print "Fired filament!"
        sleep(120.0)

    def conditional_load(target_deltaf=7.0E6, target_Q=9000):
        """
        Fires the filament until a minimum resonance frequency difference has been satisfied
        and a Q > 9000 has been satisfied.
        :param target_deltaf: Positive frequency difference in Hz
        :return:
        """
        abs_deltaf = 1e9
        Q = 0
        # Set both the Q and deltaf threshold to something low if you want it to continue after the first load
        while not (Q > target_Q and abs_deltaf > target_deltaf):
            unload_with_filament()
            load_resonator_not_trap()
            set_voltages(0.6, -2.0, None, None)
            sleep(2.0)
            if averages > 1:
                fpts, mags, phases = nwa.take_one_averaged_trace()
            else:
                fpts, mags, phases = nwa.take_one()
            f0, Q = fit_res_gerwin(fpts, mags, span=3E6)
            abs_deltaf = np.abs(f0-6.40511e9)
            print "Fit result after loading: delta f = %.2f MHz and Q = %.0f" % (abs_deltaf/1E6, Q)

        not_settled = True
        stable_temp = 0.550
        # print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
        while not_settled:
            temperature = fridge.get_mc_temperature()
            if temperature <= stable_temp:
                not_settled = False

        return f0, Q

    nwa.set_measure('S21')
    unload()

    load_electrons = True

    power = -40
    averages = 100
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

    vtrap_park = 0.330
    # vtrap_unload = 0.200
    dV = +0.010 if vtrap_unload > vtrap_park else -0.010
    vrg_isolate = -0.600
    v1 = np.array(np.arange(-2.000, 0.000+0.050, 0.050).tolist() + np.arange(0.000, vtrap_park+0.010, 0.010).tolist())
    v2 = np.array(np.arange(0.000, -0.300-0.001, -0.001).tolist() + np.arange(-0.300, vrg_isolate-0.010, -0.010).tolist())
    v3 = np.array(np.arange(vtrap_park, vtrap_unload, dV).tolist() + np.arange(vtrap_unload, vtrap_park-dV, -dV).tolist())
    v4 = v2[::-1]

    Vtraps = np.array(v1.tolist() + list(v1[-1] * np.ones(len(v2))) + v3.tolist() + list(v3[-1] * np.ones(len(v4))))
    Vress = 0.60 * np.ones(len(v1) + len(v2) + len(v3) + len(v4))
    Vresguards = np.array(list(0.00 * np.ones(len(v1))) + v2.tolist() + list(v2[-1] * np.ones(len(v3))) + v4.tolist())

    # v1 = np.arange(-2.000, 0.000, 0.050).tolist() + np.arange(0.000, 0.200+0.010, 0.010).tolist()
    # v2 = np.zeros(1) #np.arange(0.000, 0.000, -0.010)
    # v3 = np.arange(0.200, 1.500+0.010, 0.010)
    #
    # Vtraps = np.array(v1 + list(v1[-1] * np.ones(len(v2))) + v3.tolist())
    # Vress = 0.60 * np.ones(len(v1) + len(v2) + len(v3))
    # Vresguards = np.array(list(0.00 * np.ones(len(v1))) + v2.tolist() + list(v2[-1] * np.ones(len(v3))))

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

    # plt.show()

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    #unload_with_filament()

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')
    nwa.set_average_state(True)

    if load_electrons:
        target_deltaf = 7.0E6
        target_Q = 9200
        # Unload and then load once
        f0, Q = conditional_load(target_deltaf=target_deltaf, target_Q=target_Q)
        Q_pre_meas = 0
        while Q_pre_meas < target_Q:
            # Try to adjust the electron density on the resonator:
            tries = 0
            dataCache.post("f0_pre_meas", f0)
            dataCache.post("Q_pre_meas", Q)
            abs_deltaf = np.abs(f0 - 6.40511e9)
            while (abs_deltaf > target_deltaf) and (tries < 15):
                tries += 1
                if (abs_deltaf - target_deltaf) < 0.15E6 and tries == 0:
                    # Don't bother unloading; the first unload shows a really strong decrease.
                    break
                else:
                    unload_voltage = -0.25

                for i, poo in enumerate([unload_voltage, 0.6]):
                    set_voltages(poo, None, None, None)
                    sleep(2.0)
                    if poo == 0.6:
                        if averages > 1:
                            fpts, mags, phases = nwa.take_one_averaged_trace()
                        else:
                            fpts, mags, phases = nwa.take_one()
                        f0, Q = fit_res_gerwin(fpts, mags, span=3E6)

                        dataCache.post("f0_pre_meas", f0)
                        dataCache.post("Q_pre_meas", Q)
                        abs_deltaf = np.abs(f0 - 6.40511e9)
                        print "\t%d. delta f = %.2f MHz and Q = %.0f" % (i, abs_deltaf / 1E6, Q)

            Q_pre_meas = Q
            # If after adjusting the density the Q falls below 9000, start over
            if Q < target_Q:
                print "Retrying load, Q < %.0f after adjusting electron density..." % (target_Q)
                f0, Q = conditional_load(target_deltaf=target_deltaf, target_Q=target_Q)


        sleep(120)

    nwa.set_center_frequency(f0+0.5E6)
    nwa.set_span(2.5E6)
    print "Set center frequency to %.6f GHz (shift = %.2f MHz)"%(f0/1E9, (f0-6.40511e9)/1E6)

    # set_voltages(None, None, -0.30, -0.30)
    print "Starting resV sweep..."
    set_voltages(Vress[0], Vtraps[0], Vresguards[0], None, -1.00)
    for Vres, Vtrap, Vresguard in tqdm(zip(Vress, Vtraps, Vresguards)):
        set_voltages(Vres, Vtrap, Vresguard, None)
        take_trace_and_save(averages)

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

