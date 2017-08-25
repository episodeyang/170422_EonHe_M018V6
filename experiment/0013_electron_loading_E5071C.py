from ehe_experiment import eHeExperiment
from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, seekat, heman, nwa, filament
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from shutil import copyfile

this_script = r"0013_electron_loading_E5071C.py"

#res = seekat
t0 = time()

def set_voltages(res, trap):
    seekat.set_voltage(1, res)
    seekat.set_voltage(2, trap)

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
    expt_path = os.path.join(r'S:\_Data\170422 - EonHe M018V6 with L3 etch\data', today, "%s_electron_loading_500mK" % now)
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


    def take_trace_and_save(averages):
        temperature = fridge.get_mc_temperature()
        dataCache.post('temperature', temperature)

        Vres, Vtrap = get_voltages() #res.get_voltage(1.0)
        dataCache.post('Vres', Vres)
        dataCache.post('Vtrap', Vtrap)
        dataCache.post('Vpinch', seekat.get_voltage(3))

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

    def check_loading(V1=3.0, V2=0.4, threshold=5):
        fig = plt.figure()
        #res.set_voltage(1, V1)
        set_voltages(V1, V1)
        fpts, mags, phases = nwa.take_one()
        plt.plot(fpts, mags, label='%.2fV'%V1)
        max_idx = np.argmax(mags)
        initial_f0 = fpts[max_idx]
        transmission_i = mags[max_idx]
        #res.set_voltage(1, V2)
        set_voltages(V2, V2)
        sleep(1)
        fpts, mags, phases = nwa.take_one()
        plt.plot(fpts, mags, label='%.2fV'%V2)
        final_f0 = fpts[np.argmax(mags)]
        transmission_f = mags[max_idx]
        #res.set_voltage(1, V1)
        set_voltages(V1, V1)
        sleep(1)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Transmission")
        plt.legend(edgecolor='none', framealpha=1, loc=0, prop={"size":10})
        fig.savefig(os.path.join(expt_path, "Check_Loading.png"), dpi=200)
        plt.show()

        if np.abs(transmission_f - transmission_i) > threshold: #np.abs(final_f0 - initial_f0) > threshold:
            print "Electrons seem present"
            return True
        else:
            print "Shift too low! Measured shift was roughly %.2f kHz"%((final_f0 - initial_f0)/1E3)
            return False

    nwa.set_measure('S21')

    load_electrons = True
    # if not check_loading():
    #     load_electrons = True
    # else:
    #     load_electrons = False

    power = -40
    averages = 1
    sweep_points = 1601

    nwa.set_trigger_source('BUS')
    nwa.set_format('SLOG')

    nwa_config = {'start': 6.385E9,
                  'stop': 6.407E9,
                  'sweep_points': sweep_points,
                  'power': power,
                  'averages': averages,
                  'ifbw': nwa.get_ifbw()}

    nwa.configure(**nwa_config)
    dataCache.set_dict('nwa_config', nwa_config)

    #correct_delay = calibrate_electrical_delay(68E-9)
    #print correct_delay
    #nwa.set_electrical_delay(correct_delay)
    nwa.auto_scale()

    dV = 0.02

    Vress = list(np.arange(3.0, 0.0, -dV)) \
            + list(np.arange(0.0, 3.0, +dV))

    fig = plt.figure(figsize=(8.,12.))
    plt.subplot(311)
    plt.plot(Vress, 'o', color="#23aaff", markeredgecolor="none")
    plt.ylabel("Resonator voltage (V)")

    if averages > 1:
        fpts, mags, phases = nwa.take_one_averaged_trace()
    else:
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
        #res.set_voltage(1, 3.0)
        set_voltages(3.0, 3.0)
        sleep(2.0)
        filament.fire_filament(100, 0.01)
        sleep(30.0)

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

    seekat.set_voltage(3, 0)

    if check_loading():
        print "Starting resV sweep..."
        for Vres in tqdm(Vress):
            #print seekat.get_voltage(3)
            #res.set_voltage(1, Vres)
            set_voltages(Vres, Vres)
            take_trace_and_save(averages)

        nwa.set_format('MLOG')
        nwa.auto_scale()
        nwa.set_trigger_source('INT')
    else:
        print "Did not start sweep, electrons seemed not present."
