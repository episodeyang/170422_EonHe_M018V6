#from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, yoko1, yoko2, nwa, filament
from resonance_fitting import fit_res_gerwin
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0021_electron_loading_on_phase_slope_E5071C.py"
current_readout_freq = nwa.get_center_frequency()
#res = seekat
t0 = time()
expt = 'determine_mu'

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_%s" % (now, expt))
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

    for yoko in [yoko1, yoko2]:
        yoko.set_mode('VOLT')
        yoko.set_voltage_limit(10)
        yoko.set_output(True)

    def set_voltages(res, trap, res_guard, trap_guard, pinch=None, verbose=True):
        if res is not None:
            seekat.set_voltage(1, res, verbose=verbose)
        if trap is not None:
            yoko1.set_volt(trap)
            #seekat.set_voltage(2, trap, verbose=verbose)
        if res_guard is not None:
            yoko2.set_volt(res_guard)
            #seekat.set_voltage(3, res_guard, verbose=verbose)
        if trap_guard is not None:
            seekat.set_voltage(4, trap_guard, verbose=verbose)
        if pinch is not None:
            seekat.set_voltage(5, pinch, verbose=verbose)

        dataCache.post("voltage_log", np.array([time(),
                                                seekat.get_voltage(1), yoko1.get_volt(),
                                                yoko2.get_volt(), seekat.get_voltage(4),
                                                seekat.get_voltage(5)]))

    def get_voltages(active_electrodes=[np.nan]*5):
        ret = active_electrodes
        for k in np.where(np.isnan(active_electrodes))[0]:
            if k == 1:
                # Trap electrode
                ret[1] = yoko1.get_volt()
            elif k == 2:
                # Resonator guard electrode
                ret[2] = yoko2.get_volt()
            else:
                ret[k] = seekat.get_voltage(k+1)
        return ret

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

    def take_trace_and_save(averages, active_electrodes=[True]*5):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        Vres, Vtrap, Vrg, Vtg, Vpinch = get_voltages(active_electrodes)
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
        return temperature, phases

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
            sleep(10.0)

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
        filament.fire_filament(60, 0.01)
        print "Fired filament!"
        sleep(30.0)

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
            if calibration_averages > 1:
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

    power = -40
    averages = 1
    sweep_points = 401
    ifbw = 500

    calibration_averages = 50
    calibration_sweep_points = 801
    calibration_ifbw = 10E3

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    nwa_calibration_config = {'start' : 6.385E9,
                              'stop': 6.407E9,
                              'sweep_points': calibration_sweep_points,
                              'power': power,
                              'averages': calibration_averages,
                              'ifbw': calibration_ifbw}

    nwa_sweep_config = {'start': 6.385E9,
                        'stop': 6.407E9,
                        'sweep_points': sweep_points,
                        'power': power,
                        'averages': averages,
                        'ifbw': ifbw}

    nwa.configure(**nwa_calibration_config)
    nwa.set_electrical_delay(68E-9)
    nwa.set_phase_offset(180.0)
    dataCache.set_dict('nwa_calibration_config', nwa_calibration_config)
    dataCache.set_dict('nwa_sweep_config', nwa_sweep_config)
    nwa.auto_scale()

    Vtrap_park = 0.25
    presweep_refpt_max = Vtrap_park
    Vrg_isolate = -0.500 + (0.280 - Vtrap_park)
    Vtrap_unload_stop = 0.045

    # Presweep
    v1 = np.arange(-2.0, 0.0, 0.25).tolist() + np.arange(0.000, presweep_refpt_max, 0.005).tolist() + [presweep_refpt_max]
    presweep_Vress = 0.60 * np.ones(len(v1))
    presweep_Vtraps = np.array(v1)
    presweep_Vresguards = 0.00 * np.ones(len(v1))

    presweep_len = len(v1)
    presweep_refpt = presweep_Vtraps[np.argmin(np.abs(presweep_Vtraps - 0.150))]
    presweep_fthreshold = None #10E3 # Positive threshold is measured BELOW the frequency shift at the ref voltage
    presweep_phase_conversion = 0.167E-3
    presweep_phithreshold = presweep_fthreshold * presweep_phase_conversion if presweep_fthreshold is not None else None

    if expt == 'determine_mu':
        def generate_vpts(vtrap_park, vtrap_unload_stop, vrg_isolate):
            # Actual sweep
            Vtraps = np.arange(vtrap_park, 1.0, 0.0050)
            Vress = 0.60 * np.ones(len(Vtraps))
            Vresguards = np.zeros(len(Vtraps))
            return Vress, Vtraps, Vresguards
    elif 'load_unload' in expt:
        def generate_vpts(vtrap_park, vtrap_unload_stop, vrg_isolate):
            # Actual sweep
            # vtrap_park = 0.28
            # vrg_isolate = -0.500
            # vtrap_unload_stop = 0.045
            v2 = np.arange(0.000, vrg_isolate, -0.0025).tolist()
            dV = 1E-3
            v3 = list(); v4 = list()
            for vstop in [0.20, 0.15, 0.10, vtrap_unload_stop]:
                v3 += np.arange(vtrap_park, vstop - dV, -dV).tolist() + \
                      np.arange(vstop, vtrap_park + dV, +dV).tolist()
                vrg_isolate_stop = vrg_isolate + (vtrap_park - vstop)
                v4 += np.arange(vrg_isolate, vrg_isolate_stop + dV, +dV).tolist() + \
                     np.arange(vrg_isolate_stop, vrg_isolate - dV, -dV).tolist()
            v5 = np.arange(vrg_isolate, 0.000, +0.0025).tolist()
            v6 = np.arange(vtrap_park, 0.000, -0.005).tolist()
            # Make sure that v3 and v4 have the same length...
            if len(v3) > len(v4):
                v4 += np.zeros(len(v3) - len(v4)).tolist()
            elif len(v4) > len(v3):
                v3 += list(v3[-1] * np.ones(len(v4) - len(v3)))

            Vtraps = np.array(list(vtrap_park * np.ones(len(v2))) + v3 + list(vtrap_park * np.ones(len(v5))) + v6)
            Vress = 0.60 * np.ones(len(v2) + len(v3) + len(v5) + len(v6))
            Vresguards = np.array(v2 + v4 + v5 + np.zeros(len(v6)).tolist())
            return Vress, Vtraps, Vresguards

    elif expt == '2d_sweep':
        vrg_sweep = np.arange(-0.50, -0.30 + 0.0025, +0.0025)
        vtrap_sweep = np.arange(0.25, 0.10, -0.005).tolist() + np.arange(0.10, 0.25, +0.005).tolist()
        v1 = np.arange(-2.000, 0.000 + 0.050, 0.050).tolist() + np.arange(0.000, vtrap_park, 0.0025).tolist() + [vtrap_park]
        v2 = np.arange(0.000, np.min(vrg_sweep) - 0.01, -0.01).tolist()
        v3 = np.tile(vtrap_sweep, len(vrg_sweep))
        v4 = np.repeat(vrg_sweep, len(vtrap_sweep))

        Vtraps = v1 + list(v1[-1] * np.ones(len(v2))) + v3.tolist()
        Vresguards = np.zeros(len(v1)).tolist() + v2 + v4.tolist()
        Vress = 0.6 * np.ones(len(Vtraps))

        dataCache.post("data_shape", np.array([len(vtrap_sweep), len(vrg_sweep)]))

    fig = plt.figure(figsize=(8.,12.))
    plt.subplot(311)
    plt.plot(presweep_Vress, 'o', ms=3, color="#23aaff", markeredgecolor="none", label="Resonator")
    plt.plot(presweep_Vtraps, 'o', ms=3, color="#f4b642", markeredgecolor="none", label='Trap')
    plt.plot(presweep_Vresguards, 'o', ms=3, color="lawngreen", markeredgecolor="none", label='Res guard')
    sweep_Vress, sweep_Vtraps, sweep_Vresguards = generate_vpts(presweep_refpt_max, Vtrap_unload_stop, Vrg_isolate)
    plt.plot(len(presweep_Vress) + np.arange(len(sweep_Vress)), sweep_Vress, 'o', ms=3, color="#23aaff", markeredgecolor="none")
    plt.plot(len(presweep_Vtraps) + np.arange(len(sweep_Vtraps)), sweep_Vtraps, 'o', ms=3, color="#f4b642", markeredgecolor="none")
    plt.plot(len(presweep_Vresguards) + np.arange(len(sweep_Vresguards)), sweep_Vresguards, 'o', ms=3, color="lawngreen", markeredgecolor="none")
    plt.ylabel("Voltage")
    plt.xlim(0, len(sweep_Vress) + len(presweep_Vress))
    plt.legend(loc=0, prop={'size' : 8})

    if calibration_averages > 1:
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

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')
    nwa.set_average_state(True)

    f0, Q = fit_res_gerwin(fpts, mags, span=2E6)
    target_deltaf = 7.0E6
    change_readout_freq = False
    target_Q = 9200
    print "delta f = %.2f MHz and Q = %.0f" % (np.abs(f0 - 6.40511E9) / 1E6, Q)
    if np.abs(f0-6.40511E9) < (target_deltaf-0.30E6) or Q < target_Q:
        unload()
        load_electrons = True
        change_readout_freq = True

        if load_electrons:
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
                    if (abs_deltaf - target_deltaf) < 0.25E6 and tries == 1:
                        unload_voltage = -0.10
                        # Don't bother unloading; the first unload shows a really strong decrease.
                        break
                    else:
                        unload_voltage = -0.25

                    for i, poo in enumerate([unload_voltage, 0.6]):
                        set_voltages(poo, None, None, None)
                        sleep(2.0)
                        if poo == 0.6:
                            if calibration_averages > 1:
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
    else:
        print "Target deltaf and target Q already satisfied. Starting sweep right away!"

    nwa.configure(**nwa_calibration_config)
    set_voltages(presweep_Vress[0], presweep_Vtraps[0], presweep_Vresguards[0], 0.000, pinch=-1.00)
    f0, Q = fit_res_gerwin(fpts, mags, span=2E6)
    if change_readout_freq or np.abs(current_readout_freq - f0) > 150E3:
        nwa.set_center_frequency(f0)
        print "Drive frequency set to new value: Delta f = %.3f MHz"%((f0-6.40511E9)/1E6)
    else:
        nwa.set_center_frequency(f0)
        print "Drive frequency set to new value: Delta f = %.3f MHz" % ((f0 - 6.40511E9) / 1E6)
    p1, p2, p3, constant_Vtrapguard, constant_Vpinch = get_voltages()

    # Presweep
    for k, voltages in tqdm(enumerate(zip(presweep_Vress, presweep_Vtraps, presweep_Vresguards))):
        Vres, Vtrap, Vresguard = voltages[0], voltages[1], voltages[2]
        set_voltages(Vres, Vtrap, Vresguard, None)

        if not(k%40) and (k != len(presweep_Vress)-1):
            print "\n%d - Calibrating..."%k
            nwa.configure(start=nwa.get_center_frequency()-0.75E6,
                          stop=nwa.get_center_frequency()+0.75E6,
                          ifbw=calibration_ifbw,
                          sweep_points=calibration_sweep_points,
                          averages=calibration_averages)
            fpts, mags, phases = nwa.take_one_averaged_trace()
            f0, Q = fit_res_gerwin(fpts, mags, span=1.5E6)
            # print "Set center frequency to %.6f GHz (shift = %.2f MHz)" % (f0 / 1E9, (f0 - 6.40511e9) / 1E6)
            nwa.configure(span=0E6, ifbw=ifbw,
                          sweep_points=sweep_points,
                          averages=averages)
            nwa.auto_scale()

            dataCache.post('calibration_idx', k)
            dataCache.post('calibration_fpts', fpts)
            dataCache.post('calibration_mags', mags)
            dataCache.post('calibration_phases', phases)

            nwa.set_format('SLOG')
            nwa.set_trigger_source('BUS')

        active_electrodes = [np.nan]*5
        active_electrodes[0] = Vres if presweep_Vress[k] == presweep_Vress[k-1] else np.nan
        active_electrodes[1] = Vtrap if presweep_Vtraps[k] == presweep_Vtraps[k - 1] else np.nan
        active_electrodes[2] = Vresguard if presweep_Vresguards[k] == presweep_Vresguards[k - 1] else np.nan
        active_electrodes[3] = constant_Vtrapguard
        active_electrodes[4] = constant_Vpinch

        temperature, presweep_phase = take_trace_and_save(averages, active_electrodes)

        if presweep_fthreshold is not None:
            if Vtrap == presweep_refpt:
                phi_refpt = np.mean(presweep_phase)
                print "Reference point is %.2f deg at Vtrap = %.3f" % (phi_refpt, Vtrap)
                print "Waiting for %.2f deg drop..." % (presweep_phithreshold)


            if (Vtrap == presweep_Vtraps[-1]):
                print "Failed to reach the required presweep threshold. Starting the sweep at Vtrap_park = %.3f" % (
                Vtrap)
                # Generate the rest of the sweep
                Vress, Vtraps, Vresguards = generate_vpts(Vtrap, Vtrap_unload_stop, Vrg_isolate)
            elif (Vtrap > presweep_refpt):
                presweep_phi = np.mean(presweep_phase)
                print presweep_phi
                if presweep_phi < phi_refpt - presweep_phithreshold:
                    print "The presweep threshold was met at Vtrap_park = %.3f" % (Vtrap)
                    # Generate the rest of the sweep
                    Vress, Vtraps, Vresguards = generate_vpts(Vtrap, Vtrap_unload_stop, Vrg_isolate)
                    break
        else:
            if (Vtrap == presweep_Vtraps[-1]):
                Vress, Vtraps, Vresguards = generate_vpts(Vtrap, Vtrap_unload_stop, Vrg_isolate)

    # Actual sweep
    for m, voltages in tqdm(enumerate(zip(Vress, Vtraps, Vresguards))):
        Vres, Vtrap, Vresguard = voltages[0], voltages[1], voltages[2]
        set_voltages(Vres, Vtrap, Vresguard, None)

        if not (m % 40) or (m == len(Vress) - 1):
            print "\n%d - Calibrating..." % m
            nwa.configure(start=nwa.get_center_frequency() - 0.75E6,
                          stop=nwa.get_center_frequency() + 0.75E6,
                          ifbw=calibration_ifbw,
                          sweep_points=calibration_sweep_points,
                          averages=calibration_averages)
            fpts, mags, phases = nwa.take_one_averaged_trace()
            f0, Q = fit_res_gerwin(fpts, mags, span=1.5E6)
            # print "Set center frequency to %.6f GHz (shift = %.2f MHz)" % (f0 / 1E9, (f0 - 6.40511e9) / 1E6)
            nwa.configure(span=0E6, ifbw=ifbw,
                          sweep_points=sweep_points,
                          averages=averages)
            nwa.auto_scale()

            dataCache.post('calibration_idx', m+k)
            dataCache.post('calibration_fpts', fpts)
            dataCache.post('calibration_mags', mags)
            dataCache.post('calibration_phases', phases)

            nwa.set_format('SLOG')
            nwa.set_trigger_source('BUS')

        active_electrodes = [np.nan] * 5
        active_electrodes[0] = Vres if Vress[m] == Vress[m - 1] else np.nan
        active_electrodes[1] = Vtrap if Vtraps[m] == Vtraps[m - 1] else np.nan
        active_electrodes[2] = Vresguard if Vresguards[m] == Vresguards[m - 1] else np.nan
        active_electrodes[3] = constant_Vtrapguard
        active_electrodes[4] = constant_Vpinch

        take_trace_and_save(averages, active_electrodes)

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

