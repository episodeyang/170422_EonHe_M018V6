from time import sleep
from setup_instruments import nwa
from resonance_fitting import fit_res_gerwin
from slab.instruments import BNCAWG
import numpy as np
from tabulate import tabulate
from tqdm import tqdm

bnc1 = BNCAWG(address="192.168.14.143")
bnc2 = BNCAWG(address="192.168.14.150")
trigger = BNCAWG(address="192.168.14.149")

def get_idle_value(bnc, sweep_up=True):
    offset = bnc.get_offset()
    amplitude = bnc.get_amplitude()
    V1 = 0.5 * (2*offset + amplitude)
    V2 = 0.5 * (2*offset - amplitude)
    return V2 if sweep_up else V1

def change_sweep_bounds(bnc, Vi, Vf):
    #print "Offset : %.3f \tAmplitude: %.3f" % ((Vi + Vf) / 2., abs(Vi - Vf))
    bnc.set_autorange('OFF')
    bnc.set_offset((Vi + Vf) / 2.)
    bnc.set_amplitude(abs(Vi - Vf))
    return None

def setup_calibration_trace(averages, sweep_points):
    nwa.set_trigger_source('BUS')
    nwa.set_averages(averages)
    nwa.set_average_state(True)
    nwa.clear_averages()
    nwa.set_format('SLOG')
    nwa.set_electrical_delay(68E-9)
    nwa.set_sweep_points(sweep_points)

def setup_waveforms(bnc, ch_voltage_params, sweep_time):
    Vi, Vf = ch_voltage_params
    bnc.set_output(False)
    if Vi < Vf:
        Vs = np.array(np.linspace(-0.5, 0.5, 100).tolist() + np.linspace(0.5, -0.5, 100).tolist())
    else:
        Vs = np.array(np.linspace(0.5, -0.5, 100).tolist() + np.linspace(-0.5, 0.5, 100).tolist())

    bnc.send_waveform(Vs)
    sleep(0.25)
    bnc.set_frequency(1 / (2*sweep_time))
    if Vi != Vf:
        change_sweep_bounds(bnc, Vi, Vf)
    bnc.set_output(True)
    
def setup_time_trace(averages, sweep_points, ifbw, V1i, V1f, V2i, V2f, symmetric=False, first_time=True):
    """
    :param averages:
    :param sweep_points:
    :param ifbw:
    :param V1i:
    :param V1f:
    :param V2i:
    :param V2f:
    :param symmetric:
    :param send_waveform:
    :return:
    """
    # NWA
    nwa.set_span(0)
    nwa.clear_averages()
    nwa.set_format('UPH')
    nwa.set_trigger_source('EXTERNAL')
    nwa.set_trigger_average_mode(False)
    nwa.set_averages(averages)
    nwa.set_average_state(True)
    nwa.set_trigger_low_latency(True)
    nwa.set_trigger_event('point')
    nwa.set_trigger_in_polarity(1)
    nwa.set_trigger_continuous(True)
    nwa.set_sweep_points(sweep_points)
    nwa.set_electrical_delay(68E-9)

    # There is an extra 40 us for the source to settle each point. See the manual of the E5071 and the Low Latency
    # option of the external trigger.
    trigger_period = 1 / ifbw + 40E-6
    sweep_time = sweep_points * trigger_period

    trigger.set_function('PULSE')
    trigger.set_burst_mode('triggered')
    trigger.set_burst_state(True)
    trigger.set_burst_cycles(sweep_points)
    trigger.set_trigger_out(True)
    trigger.set_trigger_slope('POS')
    trigger.set_voltage_high(5.0)
    trigger.set_voltage_low(0.0)
    trigger.set_frequency(1/trigger_period)
    trigger.set_pulse_width(trigger_period / 2.)
    trigger.set_trigger_source('BUS')
    trigger.set_output(True)

    if first_time:
        for bnc, ViVf in zip([bnc1, bnc2], [(V1i, V1f), (V2i, V2f)]):
            Vi, Vf = ViVf
            bnc.set_termination('INF')
            bnc.set_function('USER')
            if Vi != Vf:
                setup_waveforms(bnc, ViVf, sweep_time)
            bnc.set_output_polarity('normal')

            if Vi != Vf:
                bnc.set_autorange('ONCE')
                bnc.set_trigger_source('EXT')
                bnc.set_trigger_slope('POS')
                bnc.set_burst_mode('triggered')
                bnc.set_burst_state(True)
                bnc.set_burst_phase(0.0)
                bnc.set_burst_cycles(1)
                bnc.set_output(True)
            else: # Disable this BNC
                bnc.set_trigger_source('MAN')
                #bnc.set_output(True)
                #bnc.set_burst_state(True)

def run(V1i, V1f, V2i, V2f, calibration_averages=20, calibration_sweep_points=1601, timetrace_averages=100,
        sweep_points=1000, IFBW=20E3, datafile=None, first_time=True):

    nwa.configure(ifbw=IFBW)

    nwa.set_average_state(state=True)
    nwa.set_trigger_average_mode(state=True)
    nwa.auto_scale()

    symmetric_sweep = True
    nwa.set_span(0E6)

    trigger_period = 1 / float(IFBW) + 40E-6
    sweep_time = sweep_points * trigger_period
    min_retrigger_time = 2 * sweep_time + 0.001

    print("Starting diagonal sweep trace with the following axis settings:")
    print(tabulate([[1, V1i, V1f, (V1f-V1i)/sweep_points * 1E3, timetrace_averages, sweep_time*1E3],
                    [2, V2i, V2f, (V2f-V2i)/sweep_points * 1E3, timetrace_averages, sweep_time*1E3]],
                   headers=['Axis', 'Start (V)', 'Stop (V)', 'Resolution (mV)', 'Averages', 'Measurement time (ms)']))

    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, V1i, V1f, V2i, V2f,
                     symmetric=symmetric_sweep, first_time=first_time)
    sweep_times = np.linspace(0, nwa.get_sweep_time(), sweep_points)
    sleep(1.0)

    for p in tqdm(range(timetrace_averages)):
        trigger.trigger()
        sleep(min_retrigger_time + np.random.uniform(0.00, 0.005))

    # Get the data
    nwa.set_format('SLOG')
    fpts, mags, phases = nwa.read_data()

    if datafile is not None:
        datafile.post('fast_fpts', fpts)
        datafile.post('fast_mags', mags)
        datafile.post('fast_phases', phases)

    nwa.set_format('UPH')
    nwa.clear_averages()
    sleep(1.0)

    # Calibrate
    nwa.configure(start=nwa.get_center_frequency() - 0.75E6,
                  stop=nwa.get_center_frequency() + 0.75E6,
                  ifbw=IFBW,
                  sweep_points=calibration_sweep_points,
                  averages=calibration_averages)
    setup_calibration_trace(calibration_averages, calibration_sweep_points)
    fpts, mags, phases = nwa.take_one_averaged_trace()
    nwa.set_trigger_continuous(False)

    if datafile is not None:
        datafile.post('calibration_fpts', fpts)
        datafile.post('calibration_mags', mags)
        datafile.post('calibration_phases', phases)
        datafile.post('sweep_times', sweep_times)
        datafile.post('sweep_voltage_1', np.linspace(V1i, V1f, sweep_points))
        datafile.post('sweep_voltage_2', np.linspace(V2i, V2f, sweep_points))

    f0, Q = fit_res_gerwin(fpts, mags)
    print (f0 - 6.40511E9) / 1E6, Q
    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, V1i, V1f, V2i, V2f, symmetric=symmetric_sweep, first_time=False)
    sleep(1.0)

if __name__ == "__main__":
    # print get_idle_value(bnc1, sweep_up=True)
    # print get_idle_value(bnc2, sweep_up=True)
    #
    # change_sweep_bounds(bnc1, -0.50, -0.30)
    # change_sweep_bounds(bnc2, 0.00, 0.20)
    #
    # run(-0.50, -0.30, 0.00, 0.20, calibration_averages=20,
    #     calibration_sweep_points=801,
    #     timetrace_averages=100,
    #     sweep_points=1000, IFBW=20E3, datafile=None, first_time=True)
    run(0, -0.30, 0.15, 0.15,
          calibration_averages=50,
          calibration_sweep_points=801,
          timetrace_averages=500,
          sweep_points=500, IFBW=20E3, datafile=None, first_time=True)