from ehe_experiment import eHeExperiment
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, heman, nwa, filament
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0016_electron_loading_2D_sweep_E5071C.py"

res_channel = 1
trap_channel = 2

def set_trap(V):
    seekat.set_voltage(trap_channel, V)

def set_res(V):
    seekat.set_voltage(res_channel, V)

def get_res():
    return seekat.get_voltage(res_channel)

def get_trap():
    return seekat.get_voltage(trap_channel)


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
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_2d_sweep" % now)
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

        Vres = get_res() #res.get_voltage(1.0)
        Vtrap = get_trap()
        ehe.dataCache.post('Vres', Vres)
        ehe.dataCache.post('Vtrap', Vtrap)

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

    load_electrons = False
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

    dVres = 0.05
    dVtrap = 0.05

    Vress = list(np.arange(1.0, -dVres, -dVres))

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
        set_res(3.0)
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

    set_res(Vress[0])

    # Set voltages for other electrodes:
    seekat.set_voltage(3, 0.0) # Resonator guard
    #seekat.set_voltage(5, 0.0) # Resonator guard

    print "Starting resV sweep..."
    for k,Vres in tqdm(enumerate(Vress)):
        set_res(Vres)
        Vtraps = list(np.arange(Vres-0.25, Vres+0.25, dVtrap)) + \
            list(np.arange(Vres+0.25, Vres-0.25-dVtrap, -dVtrap))

        if k == 0:
            ehe.dataCache.post('data_shape', (len(Vress), len(Vtraps)))

        for Vtrap in Vtraps:
            set_trap(Vtrap)
            sleep(0.25)
            take_trace_and_save()

    nwa.set_format('MLOG')
    nwa.auto_scale()
    nwa.set_trigger_source('INT')

    set_res(Vress[0])
    set_trap(0)