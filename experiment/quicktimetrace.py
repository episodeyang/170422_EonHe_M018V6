from time import sleep
from setup_instruments import nwa
from resonance_fitting import fit_res_gerwin
from slab.instruments import BNCAWG
import numpy as np
from tqdm import tqdm

bnc = BNCAWG(address="192.168.14.143")
trigger = BNCAWG(address="192.168.14.149")

def setup_calibration_trace(averages, sweep_points):
    nwa.set_trigger_source('BUS')
    nwa.set_averages(averages)
    nwa.set_average_state(True)
    nwa.clear_averages()
    nwa.set_format('SLOG')
    nwa.set_electrical_delay(68E-9)
    nwa.set_sweep_points(sweep_points)

def set_bnc_offset(voltage):
    Vi = voltage
    Vf = 0
    bnc.set_amplitude(abs(Vi - Vf))
    bnc.set_offset((Vi + Vf) / 2.)
    bnc.set_output(True)

def setup_time_trace(averages, sweep_points, ifbw, Vi, Vf, symmetric=False, send_waveform=True):
    """
    :param averages:
    :param sweep_points:
    :param ifbw:
    :param Vi:
    :param Vf:
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


    bnc.set_termination('INF')

    if not symmetric:
        symmetry = 0
        bnc.set_function('RAMP')
        bnc.set_frequency(1 / sweep_time)
    else:
        bnc.set_function('USER')
        if Vi < Vf:
            Vs = np.array(np.linspace(-0.5, 0.5, 100).tolist() + np.linspace(0.5, -0.5, 100).tolist())
        else:
            Vs = np.array(np.linspace(0.5, -0.5, 100).tolist() + np.linspace(-0.5, 0.5, 100).tolist())
        if send_waveform:
            bnc.send_waveform(Vs)
        sleep(0.25)
        bnc.set_frequency(1 / (2*sweep_time))
        bnc.set_offset((Vi+Vf)/2.)
        bnc.set_amplitude(abs(Vi-Vf))

    if Vi < Vf and not symmetric:
        bnc.set_output_polarity('inverted')
        bnc.set_symmetry(symmetry)
        bnc.set_voltage_low(np.min((Vi, Vf)))
        bnc.set_voltage_high(np.max((Vi, Vf)))
    else:
        bnc.set_output_polarity('normal')

    bnc.set_trigger_source('EXT')
    bnc.set_trigger_slope('POS')
    bnc.set_burst_mode('triggered')
    bnc.set_burst_state(True)
    bnc.set_burst_phase(0.0)
    bnc.set_burst_cycles(1)
    bnc.set_output(True)

def take_one_averaged_time_trace():
    bnc.trigger()
    nwa.get_operation_completion()
    fpts, mags, phases = nwa.read_data()

    return fpts, mags, phases

def run(Vi, Vf, calibration_averages=20, calibration_sweep_points=1601, timetrace_averages=100,
        sweep_points=1000, IFBW=20E3, datafile=None, send_waveform=True):
    # sweep_points = 1000
    # timetrace_averages = 100

    # calibration_averages = 20
    # calibration_sweep_points = 1601
    # IFBW = 20E3

    nwa.configure(ifbw=IFBW)

    nwa.set_average_state(state=True)
    nwa.set_trigger_average_mode(state=True)
    nwa.auto_scale()

    symmetric_sweep = True
    # Vi = 0.00
    # Vf = -0.50
    # trapVs = np.linspace(Vi, Vf, sweep_points)

    # setup_calibration_trace(calibration_averages, calibration_sweep_points)
    # fpts, mags, phases = nwa.take_one_averaged_trace()
    # nwa.set_trigger_continuous(False)
    # f0, Q = fit_res_gerwin(fpts, mags)
    # print (f0-6.40511E9)/1E6, Q

    # nwa.set_center_frequency(f0)
    nwa.set_span(0E6)
    # nwa.set_trigger_continuous(True)
    # fpts, mags, phases = nwa.take_one_averaged_trace()
    # nwa.set_trigger_continuous(False)

    trigger_period = 1 / float(IFBW) + 40E-6
    sweep_time = sweep_points * trigger_period
    min_retrigger_time = 2 * sweep_time + 0.005

    print "\nStarting resV sweep from %.3f to %.3f mV in %.2f ms with %d averages..." % (
    Vi * 1E3, Vf * 1E3, sweep_time * 1E3, timetrace_averages)

    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, Vi, Vf, symmetric=symmetric_sweep, send_waveform=send_waveform)
    sweep_times = np.linspace(0, nwa.get_sweep_time(), sweep_points)
    sleep(1.0)
    retrigger_time = 0.10
    retrigger_time = min_retrigger_time if retrigger_time < min_retrigger_time else retrigger_time

    for p in tqdm(range(timetrace_averages)):
        trigger.trigger()
        sleep(retrigger_time + np.random.uniform(0.00, 0.05))

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
        datafile.post('sweep_voltages', np.linspace(Vi, Vf, sweep_points))

    f0, Q = fit_res_gerwin(fpts, mags)
    print (f0 - 6.40511E9) / 1E6, Q
    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, Vi, Vf, symmetric=symmetric_sweep, send_waveform=False)
    sleep(1.0)

if __name__ == "__main__":
    run(0.00, -0.50, calibration_averages=20,
        calibration_sweep_points=801,
        timetrace_averages=100,
        sweep_points=1000, IFBW=20E3, datafile=None)