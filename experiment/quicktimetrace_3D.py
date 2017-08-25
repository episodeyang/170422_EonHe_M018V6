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

def construct_voltage_trace(V1, V2, V3, sweep_points, include_offset=False):
    # alpha = np.abs((V3 - V2) / (V2 - V1))
    # M = np.round(alpha / (1 + alpha) * sweep_points)
    # N = sweep_points - M
    N, M = sweep_points

    if V1 == V2 == V3:
        print "OK I can't do this, you need to use the DC function of the BNC!"
    elif V2 == V3:
        V3_prime = 0.5 if V3 > V1 else -0.5
        V2_prime = V3_prime
        V1_prime = -V3_prime
    elif V1 == V2:
        V1_prime = 0.5 if V3 < V1 else -0.5
        V2_prime = V1_prime
        V3_prime = -V1_prime
    else:
        if V3 > V2 > V1:
            V3_prime = 0.5
            V1_prime = -0.5
            V2_prime = 0.5 - (V3 - V2) / (V3 - V1)
        elif (V1 < V2) and (V3 < V2):
            if V3 < V1:
                V2_prime = +0.5
                V3_prime = -0.5
                V1_prime = 0.5 + (V1 - V2) / (V2 - V3)
            else:
                V1_prime = -0.5
                V2_prime = 0.5
                V3_prime = 0.5 - (V2 - V3) / (V2 - V1)
        elif V3 < V2 < V1:
            V1_prime = 0.5
            V3_prime = -0.5
            V2_prime = (V2 - V3) / (V1 - V3) - 0.5
        else:
            if V3 > V1:
                V3_prime = 0.5
                V2_prime = -0.5
                V1_prime = (V1 - V2) / (V3 - V2) - 0.5
            else:
                V1_prime = 0.5
                V2_prime = -0.5
                V3_prime = (V3 - V2) / (V1 - V2) - 0.5

    Vs = np.linspace(V1_prime, V2_prime, np.int(N)).tolist() \
         + np.linspace(V2_prime, V3_prime, np.int(M)).tolist()
    Vs += Vs[::-1]
    Vs = np.array(Vs)

    if include_offset:
        Vmin, Vmax = np.min([V1, V2, V3]), np.max([V1, V2, V3])
        amplitude = np.abs(Vmax - Vmin)
        offset = (Vmax + Vmin) / 2.
        Vs = amplitude*Vs + offset

    return Vs

def get_idle_value(bnc, sweep_up=True):
    offset = bnc.get_offset()
    amplitude = bnc.get_amplitude()
    V1 = 0.5 * (2*offset + amplitude)
    V2 = 0.5 * (2*offset - amplitude)
    return V2 if sweep_up else V1

def change_sweep_bounds(bnc, Vi, Vf):
    # print "Offset : %.3f \tAmplitude: %.3f" % ((Vi + Vf) / 2., abs(Vi - Vf))
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

def setup_waveforms(bnc, ch_voltage_params, sweep_points, sweep_time):
    bnc.set_termination('INF')
    bnc.set_function('USER')
    
    # NOTE!!!
    bnc.set_output(False)

    V1, V2, V3 = ch_voltage_params
    Vs = construct_voltage_trace(V1, V2, V3, sweep_points)
    Vmin, Vmax = np.min([V1, V2, V3]), np.max([V1, V2, V3])

    bnc.send_waveform(Vs)
    sleep(0.25)
    bnc.set_frequency(1 / (2*sweep_time))
    change_sweep_bounds(bnc, Vmin, Vmax)
    bnc.set_output_polarity('normal')
    # bnc.set_autorange('ONCE')
    bnc.set_trigger_source('EXT')
    bnc.set_trigger_slope('POS')
    bnc.set_burst_mode('triggered')
    bnc.set_burst_state(True)
    bnc.set_burst_phase(0.0)
    bnc.set_burst_cycles(1)
    bnc.set_output(True)
    
def setup_time_trace(averages, sweep_points, ifbw, ch1_voltage_params, ch2_voltage_params, 
                     measure_downsweep_too=True, first_time=True):
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
    if measure_downsweep_too:
        nwa.set_sweep_points(2*np.sum(sweep_points))
    else:
        nwa.set_sweep_points(np.sum(sweep_points))
    nwa.set_electrical_delay(68E-9)

    # There is an extra 40 us for the source to settle each point. See the manual of the E5071 and the Low Latency
    # option of the external trigger.
    trigger_period = 1 / ifbw + 40E-6
    sweep_time = np.sum(sweep_points) * trigger_period

    trigger.set_function('PULSE')
    trigger.set_burst_mode('triggered')
    trigger.set_burst_state(True)
    if measure_downsweep_too:
        trigger.set_burst_cycles(2*np.sum(sweep_points))
    else:
        trigger.set_burst_cycles(np.sum(sweep_points))
    trigger.set_trigger_out(True)
    trigger.set_trigger_slope('POS')
    trigger.set_voltage_high(5.0)
    trigger.set_voltage_low(0.0)
    trigger.set_frequency(1/trigger_period)
    trigger.set_pulse_width(trigger_period / 2.)
    trigger.set_trigger_source('BUS')
    trigger.set_output(True)

    if first_time:
        for bnc, voltage_params in zip([bnc1, bnc2], [ch1_voltage_params, ch2_voltage_params]):
            setup_waveforms(bnc, voltage_params, sweep_points, sweep_time=sweep_time)

def run(ch1_voltage_params, ch2_voltage_params, calibration_averages=20, calibration_sweep_points=1601,
        timetrace_averages=100, sweep_points=(500, 500), IFBW=20E3, datafile=None, measure_downsweep_too=False, first_time=True):

    V1_ch1, V2_ch1, V3_ch1 = ch1_voltage_params
    V1_ch2, V2_ch2, V3_ch2 = ch2_voltage_params

    nwa.configure(ifbw=IFBW)
    nwa.set_average_state(state=True)
    nwa.set_trigger_average_mode(state=True)
    nwa.auto_scale()
    nwa.set_span(0E6)

    trigger_period = 1 / float(IFBW) + 40E-6
    sweep_time = np.sum(sweep_points) * trigger_period
    min_retrigger_time = 2 * sweep_time + 0.001

    print("Starting diagonal sweep trace with the following axis settings:")
    print(tabulate([[1, V1_ch1, V2_ch1, V3_ch1, np.abs(V2_ch1-V1_ch1)/sweep_points[0] * 1E6,
                     np.abs(V3_ch1-V2_ch1)/sweep_points[1] * 1E6, timetrace_averages, sweep_time*1E3],
                    [2, V1_ch2, V2_ch2, V3_ch2, np.abs(V2_ch2-V1_ch2)/sweep_points[0] * 1E6,
                     np.abs(V3_ch2-V2_ch2)/sweep_points[1] * 1E6, timetrace_averages, sweep_time*1E3]],
                   headers=['Axis', 'V1 (V)', 'V2 (V)', 'V3 (V)', 'dV12 (uV)', 'dV23 (uV)', 'Averages', 'Measurement time (ms)']))

    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, ch1_voltage_params, ch2_voltage_params, 
                     measure_downsweep_too=measure_downsweep_too, first_time=first_time)
    sweep_times = np.linspace(0, nwa.get_sweep_time(), np.sum(sweep_points))
    sleep(1.0)
    #retrigger_time = 0.005
    retrigger_time = min_retrigger_time# if retrigger_time < min_retrigger_time else retrigger_time

    for p in tqdm(range(timetrace_averages)):
        trigger.trigger()
        sleep(retrigger_time+np.random.uniform(0.000, 0.005))# + np.random.uniform(0.00, 0.05))
        if measure_downsweep_too:
            # It seems that the NWA needs tens of ms to restart a new averaging trace.
            sleep(0.060)

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
        datafile.post('sweep_voltage_1',
                      construct_voltage_trace(V1_ch1, V2_ch1, V3_ch1, sweep_points, include_offset=True)\
                          [:np.int(np.sum(sweep_points))])
        datafile.post('sweep_voltage_2',
                      construct_voltage_trace(V1_ch2, V2_ch2, V3_ch2, sweep_points, include_offset=True)\
                          [:np.int(np.sum(sweep_points))])

    f0, Q = fit_res_gerwin(fpts, mags)
    print (f0 - 6.40511E9) / 1E6, Q
    nwa.set_trigger_continuous(True)
    setup_time_trace(timetrace_averages, sweep_points, IFBW, ch1_voltage_params, ch2_voltage_params, 
                     measure_downsweep_too=measure_downsweep_too, first_time=False)
    sleep(1.0)

if __name__ == "__main__":
    # print get_idle_value(bnc1, sweep_up=True)
    # print get_idle_value(bnc2, sweep_up=True)
    #
    # change_sweep_bounds(bnc1, -0.50, -0.30)
    # change_sweep_bounds(bnc2, 0.00, 0.20)
    #
    ch1_voltage_params = (0.00, -0.30, -0.20)
    ch2_voltage_params = (0.25, 0.25, 0.20)
    run(ch1_voltage_params, ch2_voltage_params, calibration_averages=20,
        calibration_sweep_points=801,
        timetrace_averages=200,
        sweep_points=(200, 300), IFBW=20E3, datafile=None, 
        measure_downsweep_too=True, first_time=True)
    # setup_time_trace(500, 500, 20E3, 0.30, -0.02, 0.30, -0.02, symmetric=True)
    # for i in range(5):
    #     change_sweep_bounds(bnc2, 0.28-0.02*i, 0.00)
    #     sleep(1)