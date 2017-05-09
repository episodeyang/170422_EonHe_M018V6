from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import nwa, res, guard, trap, fridge, filament
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os

if __name__ == "__main__":
    today = strftime("%y%m%d")
    now = strftime("%H%M%S")
    prefix = "load_trap_and_sweep_trap"
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
    filament.setup_driver(**filamentParams)
    filament.set_query_timeout(10000)
    print filament.get_id()

    ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=False)

    print ehe.filename

    ehe.note('start experiment.')
    print fridge.get_temperature()
    ehe.sample = lambda: None
    ehe.sample.freqNoE = 6.16562e9
    ehe.sample.freqWithE = 8023438335.47

    def take_trace_and_save(sweep_points, take_temperature=True):
        # Important: need to call nwa.setup_take() before calling this.
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
        Vguard = guard.get_volt()
        ehe.dataCache.post('Vguard', Vguard)

        fpts, mags, phases = nwa.take_in_mag_phase(sweep_points)
        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('mags', mags)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('time', time() - ehe.t0)

        if take_temperature:
            return temperature

    nwa.clear_traces()
    nwa.setup_measurement('S21')
    nwa.set_query_timeout(10000)

    load_electrons = True
    sweep_points = 201
    averages = 1

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=nwa.get_power(),
                  averages=averages,
                  ifbw=nwa.get_ifbw())

    nwa.set_electrical_delay(68.414E-9)
    nwa.setup_take(averages=averages, averages_state=True)


    dV = 10E-3
    dV_fine = 2E-3
    #resVs = list(np.arange(0.0, 2.0, +dV)) + list(np.arange(2.0, -1.0, -dV)) + list(np.arange(-1.0, 0.0 + dV, +dV))
    resVs = [0.0]
    trapVs = list(np.arange(3.0, 0.5, -dV)) + \
             list(np.arange(0.5, -0.5, -dV_fine)) + list(np.arange(-0.5, 0.5, dV_fine))

    #resVs = list(np.arange(3.0, -4.0, -dV)) + list(np.arange(-4.0, +3.0 + dV, +dV))
    #resVs = list(np.arange(3.0, 0.0, -dV)) + list(np.arange(0.0, 3.0, +dV)) + \
    #        list(np.arange(3.0, -1.0, -dV)) + list(np.arange(-1.0, 3.0, +dV)) + \
    #        list(np.arange(3.0, -2.0, -dV)) + list(np.arange(-2.0, 3.0, +dV)) + \
    #        list(np.arange(3.0, -3.0, -dV)) + list(np.arange(-3.0, 3.0, +dV)) + \
    #        list(np.arange(3.0, -4.0, -dV)) + list(np.arange(-4.0, 3.0, +dV))

    #resVs_final = list(np.arange(3.0, -4.0, -dV)) + list(np.arange(-4.0, 3.0, +dV))

    plt.subplot(211)
    plt.plot(resVs, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")

    fpts, mags, phases = nwa.take_one_in_mag_phase()

    plt.subplot(212)
    plt.plot(fpts, mags, color="#F0AD32", markeredgecolor="none")
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()

    ehe.dataCache.set('puff', 100)
    ehe.dataCache.set_dict("nwa_settings", nwa.get_settings())

    print "Loading electrons..."
    if load_electrons:
        trap.set_volt(3.0)
        res.set_volt(0.0)
        sleep(1.0)
        filament.fire_filament(100, 0.01)
        sleep(10.0)

    not_settled = True
    stable_temp = 0.050
    print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
    while not_settled:
        temperature = fridge.get_mc_temperature()
        if temperature <= stable_temp:
            not_settled = False

    print "Starting resV sweep..."

    for Vtrap in tqdm(trapVs):
        res.set_volt(0.15)
        trap.set_volt(Vtrap)
        temps = take_trace_and_save(sweep_points)

    print "Unloading electrons..."
    #res.set_volt(-2.0)
    #trap.set_volt(+3.0)
    #sleep(4.0)
    #res.set_volt(+3.0)
    #trap.set_volt(+3.0)
    trap.set_volt(-4.0)
    res.set_volt(-4.0)
    sleep(0.5)
    guard.set_volt(10.0)
    sleep(2.0)
    guard.set_volt(0.0)
    res.set_volt(resVs[0])
    trap.set_volt(resVs[0])


    # print "Starting verification sweep..."
    # for Vres in tqdm(resVs):
    #     res.set_volt(Vres)
    #     trap.set_volt(Vres)
    #     temps = take_trace_and_save(sweep_points)
    #
    # # Set the network analyzer back to viewable mode
    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_continuous()
    nwa.set_sweep_mode('CONT')


