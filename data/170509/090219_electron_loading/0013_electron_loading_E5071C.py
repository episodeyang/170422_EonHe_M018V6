from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import fridge, res, heman, nwa, filament
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0013_electron_loading_E5071C.py"

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
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_electron_loading" % now)
    print "Saving data in %s" % expt_path
    if not os.path.isdir(os.path.split(expt_path)[0]):
        os.mkdir(os.path.split(expt_path)[0])
    if not os.path.isdir(expt_path):
        os.mkdir(expt_path)
    sleep(1)

    copyfile(os.path.join(r"S:\_Data\170422 - EonHe M018V6 with L3 etch\experiment", this_script),
             os.path.join(expt_path, this_script))

    prefix = "electron_loading"
    fridgeParams = {'wait_for_temp': 0.080,
                    'min_temp_wait_time': 60}

    filamentParams = {"amplitude": 4.2,
                      "offset": -0.5,
                      "frequency": 113e3,
                      "duration": 40e-3}

    pulseParams = {"delay": .01,
                   "pulses": 150}

    # filament = FilamentDriver(address="192.168.14.144")
    filament.setup_driver(**filamentParams)
    filament.set_timeout(10000)
    print filament.get_id()

    ehe = eHeExperiment(expt_path, prefix, fridgeParams, newDataFile=True)
    print ehe.filename

    ehe.sample = lambda: None
    ehe.sample.freqNoE = 6.16562e9
    ehe.sample.freqWithE = 8023438335.47


    def take_trace_and_save():
        temperature = fridge.get_mc_temperature()
        ehe.dataCache.post('temperature', temperature)

        Vres = res.get_voltage(1.0)
        ehe.dataCache.post('Vres', Vres)

        #Vguard = guard.get_volt()
        #ehe.dataCache.post('Vguard', Vguard)

        #Vtrap = trap.get_volt()
        #ehe.dataCache.post('Vtrap', Vtrap)

        fpts, mags, phases = nwa.take_one()
        ehe.dataCache.post('fpts', fpts)
        ehe.dataCache.post('mags', mags)
        ehe.dataCache.post('phases', phases)
        ehe.dataCache.post('time', time() - ehe.t0)

        return temperature

    nwa.set_measure('S21')

    load_electrons = True
    averages = 1
    sweep_points = 1601

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    nwa.configure(center=nwa.get_center_frequency(),
                  span=nwa.get_span(),
                  sweep_points=sweep_points,
                  power=nwa.get_power(),
                  averages=averages,
                  ifbw=nwa.get_ifbw())

    #correct_delay = calibrate_electrical_delay(68E-9)
    #print correct_delay
    #nwa.set_electrical_delay(correct_delay)
    nwa.auto_scale()

    dV = 0.020

    Vress = list(np.arange(3.0, -3.0, -dV)) \
            + list(np.arange(-3.0, 3.0, +dV))

    fig = plt.figure(figsize=(8.,12.))
    plt.subplot(311)
    plt.plot(Vress, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")

    fpts, mags, phases = nwa.take_one()

    plt.subplot(312)
    plt.plot(fpts, mags)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (W)')
    plt.xlim(np.min(fpts), np.max(fpts))

    plt.subplot(313)
    plt.plot(fpts, phases)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (deg)')
    plt.xlim(np.min(fpts), np.max(fpts))
    plt.show()

    fig.savefig(os.path.join(expt_path, "pre_electron_loading.png"), dpi=200)

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    print "Loading electrons..."
    if load_electrons:
        #trap.set_volt(3.0)
        res.set_voltage(1, 3.0)
        sleep(2.0)
        filament.fire_filament(100, 0.01)
        sleep(10.0)

    not_settled = True
    stable_temp = 0.170
    print "Waiting for temperature to stabilize to %.0f mK..." % (stable_temp * 1E3)
    while not_settled:
        temperature = fridge.get_mc_temperature()
        if temperature <= stable_temp:
            not_settled = False

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    # Set voltages for other electrodes:
    res.set_voltage(2, 0.0) # DC bias pinch
    res.set_voltage(3, 0.0) # Resonator guard

    print "Starting resV sweep..."
    for Vres in tqdm(Vress):
        res.set_voltage(1, Vres)
        take_trace_and_save()

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')
