from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import nwa, res, fridge, trap
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os, sys
from slab import dsfit

sys.path.append(r'S:\_Data\160603 - EonHe M016v5\modules')
from Common import common, kfit

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    prefix = "2D_sweep"
    expt_path = os.path.join(r'S:\_Data\160603 - EonHe M016v5\data', today, "%s_%s" % (now, prefix))
    print "Saving data in %s" % expt_path
    if not os.path.isdir(expt_path):
        os.mkdir(expt_path)


    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    filamentParams = {"amplitude": 4.2,
                      "offset": -0.5,
                      "frequency": 113e3,
                      "duration": 40e-3}

    pulseParams = {"delay": .01,
                   "pulses": 150}

    #filament = FilamentDriver(address="192.168.14.144")
    #filament.setup_driver(**filamentParams)
    #print filament.get_id()

    ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=False)

    print ehe.filename

    ehe.note('start experiment.')
    print fridge.get_temperature()
    ehe.sample = lambda: None
    ehe.sample.freqNoE = 6.16562e9
    ehe.sample.freqWithE = 8023438335.47

    def take_trace_and_save(sweep_points, take_temperature=True):
        # ~ 600ms
        if take_temperature:
            temperature = fridge.get_mc_temperature()
            ehe.dataCache.post('temperature', temperature)

        # ~ 20ms
        Vres = res.get_volt()
        ehe.dataCache.post('Vres', Vres)

        # ~ 3.63us because it is cached
        Vtrap = trap.get_volt()
        ehe.dataCache.post("Vtrap", Vtrap)

        # ~ 20ms
        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        fpts, mags, phases = nwa.take_one()
        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('time', time() - ehe.t0)

        if take_temperature:
            return temperature

    nwa.set_measure('S21')
    nwa.set_trigger_source('BUS')

    load_electrons = False
    sweep_points = 401
    averages = 1

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=nwa.get_power(),
                  averages=averages,
                  ifbw=nwa.get_ifbw())

    nwa.set_electrical_delay(73.0E-9)
    nwa.set_format('SLIN')
    nwa.auto_scale()

    if load_electrons:
        print "Loading electrons..."
        res.set_volt(0.0)
        sleep(1.0)
        filament.fire_filament(100, 0.01)
        sleep(10.0)

    not_settled = True
    stable_temp = 0.150
    print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
    while not_settled:
        temperature = fridge.get_mc_temperature()
        if temperature <= stable_temp:
            not_settled = False


    sweep_times = np.linspace(0, nwa.get_sweep_time(), sweep_points)
    dV = 20E-3
    dV_fine = 2E-3
    trapVs = list(np.arange(1.0, -0.5, -dV))
    resVs = list(np.arange(0.5, 0.0, -dV)) + list(np.arange(0.0, 0.5, +dV))

    ehe.dataCache.set('Vres_plot', resVs)
    ehe.dataCache.set('Vtrap_plot', trapVs)

    plt.figure(figsize=(9.,15.))
    plt.subplot(411)
    plt.plot(resVs, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")
    plt.xlim(0, len(resVs))

    nwa.set_span(15E6)
    nwa.set_average_state(True)
    nwa.set_averages(20)
    nwa.set_format('SLIN')
    fpts, mags, phases = nwa.take_one()

    smooth_diff_phases = np.diff(common.moving_average(phases, window_size=15))
    fpts_optimize = fpts[20:len(smooth_diff_phases)-20]
    smooth_diff_phases = smooth_diff_phases[20:len(smooth_diff_phases)-20]/np.diff(fpts)[0]

    print "Calibrating pump tone for optimal accuracy..."

    amp, f0, width = dsfit.fitgauss(fpts_optimize, smooth_diff_phases, no_offset=True)

    plt.subplot(412)
    plt.plot(fpts, phases, color="#F0AD32", markeredgecolor="none")
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Sensitivity (deg/Hz)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.vlines(f0, np.min(phases), np.max(phases), linestyles='--', colors='k', lw=2.0)
    plt.grid()

    plt.subplot(413)
    plt.plot(fpts_optimize, smooth_diff_phases, color="#F0AD32", markeredgecolor="none")
    plt.plot(fpts_optimize, dsfit.gaussfunc_nooffset([amp, f0, width], fpts_optimize), '-k', lw=2.0)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Sensitivity (deg/Hz)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.grid()
    plt.vlines(f0, np.min(smooth_diff_phases), np.max(smooth_diff_phases),
               linestyles='--', colors='k', lw=2.0)

    print "Optimum found for f = %.6f GHz. Setting tone."%(f0/1E9)
    print "Please verify example trace in figure."

    ehe.dataCache.set('optimize_fpts', fpts_optimize)
    ehe.dataCache.set('optimize_f0', f0)
    ehe.dataCache.set('optimize_sensitivity', smooth_diff_phases)
    ehe.dataCache.set('optimize_sensitivity_fit', dsfit.gaussfunc_nooffset([amp, f0, width], fpts_optimize))

    nwa.set_span(0E6)
    nwa.set_center_frequency(f0)
    nwa.set_average_state(True)
    nwa.set_averages(averages)
    nwa.set_format('SLIN')
    nwa.auto_scale()
    fpts, mags, phases = nwa.take_one()

    plt.subplot(414)
    plt.plot(sweep_times, phases, color="#F0AD32", markeredgecolor="none")
    plt.xlabel('Time (s)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(sweep_times), np.max(sweep_times))
    plt.grid()

    common.save_figure(plt.gcf(), save_path=expt_path)
    plt.show()

    ehe.dataCache.set('puff', 100)
    ehe.dataCache.set_dict("nwa_settings", nwa.get_settings())
    ehe.dataCache.set('sweep_pts', sweep_times)

    print "Starting 2D sweep..."

    for Vtrap in tqdm(trapVs):
        trap.set_volt(Vtrap)
        for Vres in resVs:
            res.set_volt(Vres)
            temps = take_trace_and_save(sweep_points)

    nwa.set_format('MLOG')
    nwa.set_span(15E6)
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    res.set_volt(resVs[0])
    trap.set_volt(trapVs[0])

