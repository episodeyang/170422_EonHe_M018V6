# -*- coding: utf-8 -*-

import os
from shutil import copyfile
import numpy as np
import matplotlib.pyplot as plt
import ruamel.yaml as yaml
import time
from tqdm import tqdm

import utils
from data_cache import dataCacheProxy
from visdom_helper import visdom_helper


class eHeExperiment():
    def __init__(self, config_file_path, data_directory=None, verbose=True):
        # done: load config using yaml
        with open(config_file_path, 'r') as config_file:
            # todo: save text of yaml config in datacache
            self.config = utils.Struct(**yaml.load(config_file))
            config_file.seek(0)
            self.config_text = config_file.read()

        if verbose:
            print self.config_text

        # done: create new folder for experiment
        if not data_directory:
            data_directory = self.config.data_directory

        self.config.data_directory_formatted = self.make_data_dir(
            os.path.join(
                os.getcwd(),
                data_directory.format(
                    date=time.strftime("%y%m%d"),
                    time=time.strftime("%H%M%S"),
                    prefix=self.config.prefix
                )
            )
        )
        file_path = os.path.join(self.config.data_directory_formatted, self.config.prefix + '.h5')
        copyfile(config_file_path, os.path.join(self.config.data_directory_formatted,
                                                os.path.split(config_file_path)[-1]))

        self.dataCache = dataCacheProxy(file_path, **vars(self.config.data_cache) if self.config.data_cache else {})
        self.dataCache.note(self.config_text, key_string='config_file', max_line_length=-1)

        # setup visdom dashboard
        self.dash = visdom_helper.Dashboard(self.config.prefix)

        self.reset_timer()

    def reset_timer(self):
        self.t0 = time.time()

    def make_data_dir(self, path):
        print(path)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    # def attach_instruments(self):
    #     self.im = InstrumentManager()

    def note(self, string):
        print string
        self.dataCache.note(string, max_line_length=self.config.ledger.note_line_length)

    def sweep(self, sweep_generator):

        for params in tqdm(list(sweep_generator)):
            # if k == 0:
            #     ehe.dataCache.post('data_shape', (len(Vress), len(Vtraps)))
            self.set_res_voltage(params['Vres'])
            self.set_trap_voltage(params['Vtrap'])
            self.set_guard_voltage(params['Vguard'])
            t = self.take_trace_and_save()

    def get_sweep_data(self, sweep_generator):
        data = {}
        for params in sweep_generator:
            for k in params.keys():
                if k in data:
                    data[k].append(params[k])
                else:
                    data[k] = [params[k]]
        return data

    def plot_sweep_params(self, data, index=None, title="sweep_parameters", blocking=True):
        fig = plt.figure(figsize=(8., 12.))
        plt.subplot(311)
        title = ("{:04d}_".format(index) if index != None else "") + title
        plt.title(title)

        for i, key in enumerate([k for k in data.keys() if k is not 'k']):
            plt.plot(data[key], 'o-', color=self.config.colors[i % 5], linewidth=3, markeredgecolor="none", label=key)
        plt.ylabel("Bias Voltage (V)")
        plt.legend(frameon=False)
        fpts, mags, phases = self.nwa.take_one()

        plt.subplot(312)
        plt.plot(fpts, mags, linewidth=2, color=self.config.colors[0])
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Magnitude (W)')
        plt.xlim(np.min(fpts), np.max(fpts))

        plt.subplot(313)
        plt.plot(fpts, phases, linewidth=2, color=self.config.colors[1])
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Phase (deg)')
        plt.xlim(np.min(fpts), np.max(fpts))

        if blocking:
            plt.show()

        title += ".png"
        fig.savefig(os.path.join(self.config.data_directory_formatted, title), dpi=200)

    def save_sweep_preview(self, sweep_generator, index=None, title="sweep_preview", blocking=True):
        data = self.get_sweep_data(sweep_generator)
        self.plot_sweep_params(data, index, title, blocking)

    # list of shim methods to make high-level code more shielded from low-level changes.
    def get_res_voltage(self):
        return self.seekat.get_voltage(self.config.seekat.res_channel)

    def set_res_voltage(self, volt):
        self.seekat.set_voltage(self.config.seekat.res_channel, volt)

    def get_trap_voltage(self):
        return self.seekat.get_voltage(self.config.seekat.trap_channel)

    def set_trap_voltage(self, volt):
        self.seekat.set_voltage(self.config.seekat.trap_channel, volt)

    def get_guard_voltage(self):
        return self.seekat.get_voltage(self.config.seekat.guard_channel)

    def set_guard_voltage(self, volt):
        self.seekat.set_voltage(self.config.seekat.guard_channel, volt)

    def take_trace_and_save(self):
        temperature = self.fridge.get_mc_temperature()
        self.dataCache.post('temperature', temperature)

        self.dataCache.post('Vres', self.get_res_voltage())
        self.dataCache.post('Vtrap', self.get_trap_voltage())
        self.dataCache.post('Vguard', self.get_guard_voltage())

        fpts, mags, phases = self.nwa.take_one()
        self.dataCache.post('fpts', fpts)
        self.dataCache.post('mags', mags)
        self.dataCache.post('phases', phases)
        self.dataCache.post('time', time.time() - self.t0)

        # Live plots
        self.dash.plot('nwa-monitor', 'line', X=fpts, Y=mags)
        ## heatmap of the spectrum
        self.dash.plot('spectrum-monitor', 'heatmap', X=self.dataCache.get('mags').T)
        vress, vtraps, vguards = self.dataCache.get('Vres'), self.dataCache.get('Vtrap'), self.dataCache.get('Vguard')
        self.dash.plot('bias-electrodes', 'line',
                       X=np.arange(len(vress)),
                       Y=np.column_stack((vress, vtraps, vguards))
                       )
        return temperature

    def fridge_wait_for_cooldown(self, wait_for_temp=None, min_temp_wait_time=None):
        print('waiting for fridge to cool down')
        not_settled = True
        wait_for_temp = wait_for_temp or self.config.fridge.wait_for_temp
        min_temp_wait_time = min_temp_wait_time if min_temp_wait_time is None else self.config.fridge.min_temp_wait_time
        while not_settled:
            temperature = self.fridge.get_mc_temperature()
            if temperature <= wait_for_temp and \
                            (time.time() - self.t0) > min_temp_wait_time:
                not_settled = False
                print('')
            else:
                time.sleep(5.0)
                print "temperature is {}, wait to get below {}\r".format(temperature, wait_for_temp),

    def load_electrons(self):
        self.filament.setup_driver(**self.config.filament.config)

        print("firing filament...")
        self.set_res_voltage(self.config.experiment.loading_Vres)
        self.set_trap_voltage(self.config.experiment.loading_Vtrap)
        self.set_guard_voltage(self.config.experiment.loading_Vguard)
        self.filament.fire_filament(**self.config.filament.firing)
        self.fridge_wait_for_cooldown()

        # def updateFilament(self, params):
        #     # self.note('update filament driver')
        #     self.fil.setup_driver(params['fil_amp'], params['fil_off'],
        #                           params['fil_freq'], params['fil_duration'])
        #
        # def set_DC_mode(self, trapHigh=3.5, trapLow=0):
        #     self.na.set_output('on')
        #     self.na.set_trigger_source('bus')
        #     rf_output = self.rf.get_output()
        #     self.rf.set_output(False)
        #     lo_output = self.rf.get_output()
        #     self.lo.set_output(False)
        #     try:
        #         self.trap.setup_volt_source(None, trapHigh, trapLow, 'on')
        #     except AttributeError:
        #         print 'using YokogawaGS200'
        #
        # def set_ramp_mode(self, high=None, low=None, offset=None, amp=None, symmetric=False):
        #     # if hasattr(self.trap, 'set_burst_phases'):
        #     self.set_ramp(high, low, offset, amp)
        #     self.rf.set_output(True)
        #     self.lo.set_output(True)
        #
        #     if symmetric:
        #         self.trap.set_burst_phase(90)
        #         self.trap.set_symmetry(50)
        #     else:
        #         self.trap.set_burst_phase(0)
        #         self.trap.set_symmetry(0)
        #     self.trap.set_function('ramp')
        #     self.trap.set_burst_state('on')
        #     self.trap.set_trigger_source('ext')
        #     self.na.set_output('off')
        #
        # def set_ramp(self, high=None, low=None, offset=None, amp=None):
        #     """
        #     high and low overrides amp and offset.
        #     """
        #     # if hasattr(self.trap, 'set_burst_phases'):
        #     if low != None and high != None:
        #         amp = abs(high - low)
        #         offset = max(high, low) - amp / 2.
        #     if amp != None:
        #         self.trap.set_amplitude(amp)
        #     if offset != None:
        #         self.trap.set_offset(offset)
        #
        # def get_trap_high_low(self):
        #     offset = self.trap.get_offset()
        #     amp = self.trap.get_amplitude()
        #     return offset + amp / 2.0, offset - amp / 2.0
        #
        # def nwa_sweep(self, fpts=None, config=None):
        #     """
        #     this is the alazar nwa sweep code, using the alazar homodyne setup.
        #     """
        #     if fpts == None:
        #         self.nwa.config.fpts = linspace(self.nwa.config.range[0], self.nwa.config.range[1],
        #                                         self.nwa.config.range[2])
        #     else:
        #         self.nwa.config.fpts = fpts
        #
        #     if self.alazar.config != config and config != None:
        #         print "new configuration file"
        #         self.alazar.config = AlazarConfig(config)
        #         print "config file has to pass through the AlazarConfig middleware."
        #         self.alazar.configure()
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('alazar_nwa_sweep', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #     high, low = self.get_trap_high_low()
        #     self.dataCache.set('rampHigh', high)
        #     self.dataCache.set('rampLow', low)
        #     self.dataCache.set('resV', self.res.get_volt())
        #     self.dataCache.note('ramp high: {}, low: {}'.format(high, low))
        #     self.dataCache.note('averaging(recordsPerBuffer): {}'.format(self.alazar.config.recordsPerBuffer))
        #     self.dataCache.set('fpts', self.nwa.config.fpts)
        #     start, end, n = self.nwa.config.range
        #     self.dataCache.set('fStart', start)
        #     self.dataCache.set('fEnd', end)
        #     self.dataCache.set('fN', n)
        #     self.dataCache.note('start freq: {}, end freq: {}, number of points: {}'.format(start, end, n))
        #
        #     for f in self.nwa.config.fpts:
        #         self.rf.set_frequency(float(f))
        #         tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data(excise=(0, -56))  # excise=(0,4992))
        #
        #         # ch1_avg = mean(ch1_pts)
        #         # ch2_avg = mean(ch2_pts)
        #         mags = sqrt(ch1_pts ** 2 + ch2_pts ** 2)
        #         phases = map(exp_utils.phase, zip(ch1_pts, ch2_pts))
        #
        #         self.plotter.append_z('nwa mag', mags)
        #         self.plotter.append_z('nwa phase', phases)
        #         self.plotter.append_z('nwa I', ch1_pts)
        #         self.plotter.append_z('nwa Q', ch2_pts)
        #
        #         # self.dataCache.post('mags', mags)
        #         # self.dataCache.post('phases', phases)
        #         self.dataCache.post('I', ch1_pts)
        #         self.dataCache.post('Q', ch2_pts)
        #     return mags
        #
        # def heterodyne_spectrum(self, fpts=None, config=None):
        #     if fpts == None:
        #         self.nwa.config.fpts = linspace(self.nwa.config.range[0], self.nwa.config.range[1],
        #                                         self.nwa.config.range[2])
        #     else:
        #         self.nwa.config.fpts = fpts
        #
        #     if self.alazar.config != config and config != None:
        #         print "new configuration file"
        #         self.alazar.config = AlazarConfig(config)
        #         print "config file has to pass through the AlazarConfig middleware."
        #         self.alazar.configure()
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('heterodyne_spectrum', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #     high, low = self.get_trap_high_low()
        #     self.dataCache.set('rampHigh', high)
        #     self.dataCache.set('rampLow', low)
        #     self.dataCache.set('resV', self.res.get_volt())
        #     self.dataCache.note('ramp high: {}, low: {}'.format(high, low))
        #     self.dataCache.note('averaging(recordsPerBuffer): {}'.format(self.alazar.config.recordsPerBuffer))
        #     self.dataCache.set('fpts', self.nwa.config.fpts)
        #     start, end, n = self.nwa.config.range
        #     self.dataCache.set('fStart', start)
        #     self.dataCache.set('fEnd', end)
        #     self.dataCache.set('fN', n)
        #     self.dataCache.set('IF', self.IF)
        #     self.dataCache.note('start freq: {}, end freq: {}, number of points: {}'.format(start, end, n))
        #     try:
        #         temperature = self.fridge.get_temperature()
        #     except:
        #         temperature = self.fridge.get_temperature()
        #     self.dataCache.set('temperature', temperature)
        #
        #     self.rf.set_frequency(self.nwa.config.fpts[0])
        #     self.lo.set_frequency(self.nwa.config.fpts[0] + self.IF)
        #
        #     ampI = []
        #     ampQ = []
        #     for f in self.nwa.config.fpts[1:]:
        #         tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data(excise=(0, -56))  # excise=(0,4992))
        #
        #         # place the setting here to allow time for the rf sources to stablize.
        #         self.rf.set_frequency(f)
        #         self.lo.set_frequency(f + self.IF)
        #
        #         # time.sleep(0.1)
        #         # print 'sleeping for 0.1 second'
        #
        #         dtpts, amp1, amp2 = dataanalysis.fast_digital_homodyne(tpts, ch1_pts, ch2_pts, IFfreq=self.IF,
        #                                                                AmpPhase=True)
        #         self.plotter.append_z('heterodyne spectrum mag', amp1)
        #         self.dataCache.post('amp I', amp1)
        #         self.dataCache.post('amp Q', amp2)
        #         ampI.append([amp1])
        #         ampQ.append([amp2])
        #
        #     return concatenate(ampI), concatenate(ampQ)  # , phase1 #ch1_pts, ch2_pts
        #
        # def heterodyne_resV_sweep(self, config=None, trackMode=True, trapTrack=True, trapAmp=1, offsetV=0,
        #                           trackThreshold=50e3, snapshots=None):
        #     if self.alazar.config != config and config != None:
        #         print "new configuration file"
        #         self.alazar.config = AlazarConfig(config)
        #         print "config file has to pass through the AlazarConfig middleware."
        #         self.alazar.configure()
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('heterodyne_resV_sweep', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #     if trapTrack == False:
        #         high, low = self.get_trap_high_low()
        #         self.dataCache.set('rampHigh', high)
        #         self.dataCache.set('rampLow', low)
        #         self.dataCache.note('ramp high: {}, low: {}'.format(high, low))
        #     else:
        #         self.get_peak()
        #         self.get_peak(nwa_center=self.sample.peakF, nwa_span=2e6)
        #
        #     self.dataCache.set('resVs', self.resVs)
        #     self.dataCache.note('averaging(recordsPerBuffer): {}'.format(self.alazar.config.recordsPerBuffer))
        #     self.dataCache.set('IF', self.IF)
        #     self.dataCache.set('offset_frequency', self.offsetF)
        #     try:
        #         temperature = self.fridge.get_temperature()
        #     except:
        #         temperature = self.fridge.get_temperature()
        #     self.dataCache.set('temperature', temperature)
        #
        #     self.rf.set_frequency(self.sample.peakF + self.offsetF)
        #     self.lo.set_frequency(self.sample.peakF + self.offsetF + self.IF)
        #
        #     if snapshots != None:
        #         snapshots = sorted(snapshots)
        #
        #     ampI = []
        #     ampQ = []
        #     ds = []
        #     dds = []
        #     centers = []
        #     for resV in self.resVs:
        #         self.res.set_volt(resV)
        #         print "| {:.4f}".format(resV)
        #
        #         if trapTrack:
        #             self.trap.set_amplitude(trapAmp)
        #             self.trap.set_offset(resV + offsetV)
        #             high, low = self.get_trap_high_low()
        #             self.dataCache.post('rampHighs', high)
        #             self.dataCache.post('rampLows', low)
        #
        #         if trackMode:
        #             trapHigh, trapLow = self.get_trap_high_low()
        #             self.set_DC_mode()
        #             self.get_peak(nwa_center=self.sample.peakF, nwa_span=5e6)
        #             self.dataCache.post('peakFs', self.sample.peakF)
        #             # intelligent jump detection via threshold.
        #             d = self.sample.peakF
        #             ds.append(d)
        #             n = len(ds)
        #             if n == 0:
        #                 ds = [d, ]
        #                 # dds = [0, ] # do nothing about dds.
        #                 centers.append(d)
        #             elif n == 1:
        #                 ds.append(d)
        #                 # dds.append(ds[-1] - ds[-2])
        #                 centers.append(2 * ds[-1] - 1 * ds[-2])
        #             elif n == 2:
        #                 ds.append(d)
        #                 centers.append(1.33 * ds[-1] - 0.66 * ds[-2] + 0.33 * ds[-3])
        #             else:
        #                 ds.append(d)
        #                 centers.append(1.25 * ds[-1] - 0.75 * ds[-2] + 0.25 * ds[-3] + 0.25 * ds[-4])
        #             if abs(d - centers[-1]) >= trackThreshold:
        #                 ds = []
        #
        #             self.set_ramp_mode(trapHigh, trapLow)
        #             centerF = centers[-1] + self.offsetF
        #             self.rf.set_frequency(centerF)
        #             self.lo.set_frequency(centerF + self.IF)
        #             self.dataCache.post('RFs', centerF)
        #             self.plotter.append_y('RF', centerF)
        #             print 'center frequency is {}'.format(centerF)
        #             self.plotter.append_y('peakF', self.sample.peakF)
        #
        #         tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data(excise=(0, -24))  # excise=(0,4992))
        #         dtpts, amp1, amp2 = dataanalysis.fast_digital_homodyne(tpts, ch1_pts, ch2_pts, IFfreq=self.IF,
        #                                                                AmpPhase=True)
        #         self.plotter.append_z('amp resV sweep', amp1)
        #         self.dataCache.post('amp I', amp1)
        #         self.dataCache.post('amp Q', amp2)
        #         ampI.append([amp1])
        #         ampQ.append([amp2])
        #
        #     return concatenate(ampI), concatenate(ampQ)  # , phase1 #ch1_pts, ch2_pts
        #
        # def res_set_Vs(self, resStart, resStop, resStep=None, n=None):
        #     if resStep == None:
        #         self.resVs = linspace(resStart, resStop, n)
        #     else:
        #         self.resVs = exp_utils.ramp(resStart, resStop, resStep)
        #
        # def set_ramp_stops(self, high, low, window=None, n=None):
        #     if window != None:
        #         self.rampHighs = arange(high, low, -abs(window))[:-1]
        #         self.rampLows = arange(high, low, -abs(window))[1:]
        #     elif n >= 1:
        #         self.rampHighs = linspace(high, low, n + 1)[:-1]
        #         self.rampLows = linspace(high, low, n + 1)[1:]
        #
        # def nwa_scan(self, frequency=None):
        #     """
        #     nwa scan in [window,] following resVs and rampHighs, rampLows
        #     """
        #     if frequency != None:
        #         self.lb.set_frequency(frequency)
        #         self.nwa.config.frequency = frequency
        #     else:
        #         self.nwa.config.frequency = self.lb.get_frequency()
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('alazar_single_f_resV_scan', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #     self.dataCache.note('averaging(recordsPerBuffer): {}'.format(self.alazar.config.recordsPerBuffer))
        #     self.dataCache.set('frequency', self.nwa.config.frequency)
        #
        #     tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data()
        #
        #     I_stack = []
        #     Q_stack = []
        #     mags_stack = []
        #     phases_stack = []
        #
        #     for resV in self.resVs:
        #         self.res.set_volt(resV)
        #         tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data(excise=(0, -56))  # excise=(0,4992))
        #
        #         I_half = []
        #         Q_half = []
        #
        #         for ind, high_low in enumerate(zip(self.rampHighs, self.rampLows)):
        #             group_prefix = 'ramp_{}.'.format(str(1000 + ind)[-3:])
        #
        #             self.dataCache.post(group_prefix + 'resVs', resV)
        #
        #             high, low = high_low
        #             self.set_ramp(high=high, low=low)
        #             self.dataCache.post(group_prefix + 'rampHighs', high)
        #             self.dataCache.post(group_prefix + 'rampLows', low)
        #             self.dataCache.note(group_prefix + 'ramp high: {}, low: {}'.format(high, low))
        #
        #             tpts, ch1_pts, ch2_pts = self.alazar.acquire_avg_data(excise=(0, -56))  # excise=(0,4992))
        #
        #             mags = sqrt(ch1_pts ** 2 + ch2_pts ** 2)
        #             phases = map(exp_utils.phase, zip(ch1_pts, ch2_pts))
        #
        #             I_half.extend(ch1_pts[:-len(ch1_pts) / 2])
        #             Q_half.extend(ch2_pts[:-len(ch2_pts) / 2])
        #
        #             self.dataCache.post(group_prefix + 'I', ch1_pts)
        #             self.dataCache.post(group_prefix + 'Q', ch2_pts)
        #             # self.dataCache.post('mags', mags)
        #             # self.dataCache.post('phases', phases)
        #
        #         I_stack.append(I_half)
        #         Q_stack.append(Q_half)
        #         self.plotter.append_z('nwa I', I_half)
        #         self.plotter.append_z('nwa Q', Q_half)
        #
        #     extent = [[self.rampHighs[0], 2 * self.rampLows[-1] - self.rampHighs[0]],
        #               [self.resVs[0], self.resVs[-1]]
        #               ]
        #     self.plotter.plot_z('nwa I', I_stack, extent=extent)
        #     self.plotter.plot_z('nwa Q', Q_stack, extent=extent)
        #     # self.plotter.plot_z('nwa mag', mags_stack, extent=extent)
        #     # self.plotter.plot_z('nwa phase', phases_stack, extent=extent)
        #
        # def set_alazar_average(self, average=1):
        #     self.alazar.config.recordsPerBuffer = average
        #     self.alazar.config.recordsPerAcquisition = average
        #     self.alazar.config.timeout = 1000 * average
        #     self.alazar.configure()  # self.alazar.config)
        #     # self.alazarConfig['recordsPerBuffer'] = average
        #     # self.alazarConfig['recordsPerAcquisition'] = average
        #     # self.alazar.configure(AlazarConfig(self.alazarConfig))
        #
        # def gate_sweep(self, config):
        #     print "Configuring card"
        #     scope_settings = AlazarConfig(config)
        #     card = Alazar(scope_settings)
        #     card.configure()
        #     print "Sweep gate voltage"
        #     tpts, ch1_pts, ch2_pts = card.acquire_avg_data(excise=(0, 4950))
        #
        # # def na_take_one(self, plotName='na spectrum'):
        # #     """Setup Network Analyzer to take a single averaged trace and grab data,
        # #     returning fpts, mags, phases"""
        # #     self.na.clear_averages()
        # #     self.na.trigger_single()
        # #     self.na.averaging_complete()
        # #     ans = self.na.read_data()
        # #     if plotName == None:
        # #         plotName = 'na spectrum'
        # #     self.plotter.append_z(plotName, ans[1])
        # #     return ans
        #
        # def get_na_sweep_voltage(self, center=None, span=None, npts=None, plotName=None):
        #     if center != None:
        #         self.na.set_center_frequency(center)
        #     if span != None:
        #         self.na.set_span(span)
        #     if npts != None:
        #         self.na.set_sweep_points(npts)
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('na_take_one', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #
        #     try:
        #         trapStart, trapEnd, trapStep, resStart, resEnd, resStep, doublePass = self.config.volt_sweep_range
        #         self.dataCache.note(
        #             'trapStart: {} , trapEnd: {} , trapStep: {} , resStart: {} , resEnd: {} , resStep: {} , doublePass: {} '.format(
        #                 trapStart, trapEnd, trapStep, resStart, resEnd, resStep, doublePass))
        #         self.dataCache.set('trapStart', trapStart)
        #         self.dataCache.set('trapEnd', trapEnd)
        #         self.dataCache.set('trapStep', trapStep)
        #         self.dataCache.set('resStart', resStart)
        #         self.dataCache.set('resEnd', resEnd)
        #         self.dataCache.set('resStep', resStep)
        #         self.dataCache.set('doublePass', str(doublePass))
        #     except:
        #         self.dataCache.set('resVs', self.resVs)
        #         self.dataCache.set('trapVs', self.trapVs)
        #
        #     fpts, mag, phase = self.na.take(plotName=plotName)
        #     self.dataCache.set('fpts', fpts)
        #     for trapV, resV in zip(self.trapVs, self.resVs):
        #         self.trap.set_volt(trapV)
        #         self.res.set_volt(resV)
        #         fpts, mags, phases = self.na.take(plotName=plotName)
        #         # self.dataCache.set('fpts', fpts)
        #         self.dataCache.post('mags', mags)
        #         self.dataCache.post('phases', phases)
        #         offset, amplitude, center, hwhm = dsfit.fitlor(fpts, dBmtoW(mag))
        #         self.dataCache.post('centers', center)
        #         self.plotter.append_y('centers', center)
        #
        #     offset, amplitude, center, hwhm = dsfit.fitlor(fpts, dBmtoW(mag))
        #     print "center frequency is: ", center
        #     return center
        #
        # def peak_track_voltage_sweep(self, center=None, span=None, npts=None, plotName=None, dynamicWindowing=False):
        #     '''
        #     when dynamic windowing is turned off, the peakTracker does not move
        #     the window around unless the jump is larger than 1/6th of the entire
        #     span.
        #     '''
        #     if center != None:
        #         self.na.set_center_frequency(center)
        #     # if span != None:
        #     #     self.na.set_span(span)
        #     if npts != None:
        #         self.na.set_sweep_points(npts)
        #
        #     self.dataCache.new_stack()
        #     self.dataCache.note('peak_track_voltage_sweep', key_string='type')
        #     self.dataCache.note(exp_utils.get_date_time_string(), key_string='startTime')
        #
        #     self.dataCache.set('resVs', self.resVs)
        #     self.dataCache.set('trapVs', self.trapVs)
        #     self.dataCache.set('temperature', self.fridge.get_temperature())
        #
        #     assert (self.sample.peakF, 'no peakF found, need to pre fit the peak before start the script')
        #     fpts, mag, phase = self.na.take(plotName=plotName)
        #     self.dataCache.set('fpts', fpts)
        #     centers = []
        #     for trapV, resV in zip(self.trapVs, self.resVs):
        #         print "resV: {}, trapV: {}".format(resV, trapV)
        #         self.res.set_volt(resV)
        #         self.trap.set_volt(trapV)
        #         try:
        #             dynamic_range = (centers[-1] - centers[-2]) * 6.0
        #         except (TypeError, IndexError):
        #             dynamic_range = 0
        #         if dynamic_range > span:
        #             print "peak out of dynamic window. taking intermediate peak data.---------------------"
        #             print "dynamicWindowing is :{} ======-------------------------".format(dynamicWindowing)
        #             nwa_span = dynamic_range
        #             self.get_peak(nwa_center=self.sample.peakF, nwa_span=nwa_span, npts=npts)
        #             nwa_span = span
        #             fpts, mags, phases = self.get_peak(set_nwa=True, nwa_center=self.sample.peakF, nwa_span=nwa_span,
        #                                                npts=npts)
        #         else:
        #             print "dynamicWindowing is :{} ===============================".format(dynamicWindowing)
        #             nwa_span = span
        #             fpts, mags, phases = self.get_peak(set_nwa=dynamicWindowing, nwa_center=self.sample.peakF,
        #                                                nwa_span=nwa_span, npts=npts)
        #
        #         self.dataCache.post('fptss', fpts)
        #         self.dataCache.post('mags', mags)
        #         self.dataCache.post('phases', phases)
        #         self.dataCache.post('centers', self.sample.peakF)
        #         centers.append(self.sample.peakF)
        #         self.plotter.append_y('centers {}'.format(npts), self.sample.peakF)
        #
        #     print 'done with peak track voltage sweep!'
        #
        # def set_volt_sweep(self, trapStart, trapEnd, trapStep, resStart, resEnd, resStep, doublePass=False, showPlot=False,
        #                    straight=False):
        #     self.config.volt_sweep_range = [trapStart, trapEnd, trapStep, resStart, resEnd, resStep, doublePass]
        #     if doublePass:
        #         self.pts = (((trapStart, trapEnd, trapStart), trapStep),)
        #     else:
        #         self.pts = (((trapStart, trapEnd), trapStep),)
        #     self.tvps = exp_utils.Vramps(self.pts)
        #     self.pts = (((resStart, resEnd), resStep),)
        #     self.rvps = exp_utils.Vramps(self.pts)  # , 0.25,0.1])#Vramps(pts)
        #     self.trapVs = exp_utils.flatten(outer(ones(len(self.rvps)), self.tvps))
        #     self.resVs = exp_utils.flatten(outer(self.rvps, ones(len(self.tvps))))
        #
        #     if straight:
        #         # straight flag completely overrides the sweep
        #         # problem is that two not not necessarily the same length
        #         self.resVs = exp_utils.Vramps((((resStart, resEnd), resStep),))
        #         self.trapVs = exp_utils.Vramps((((trapStart, trapEnd), trapStep),))
        #
        #     if showPlot:
        #         plt.plot(self.resVs, self.trapVs)
        #         plt.xlim(-1.6, 1.6)
        #         plt.ylim(-0.8, 1.8)
        #     print "estimated time is %d days %d hr %d minutes." % exp_utils.days_hours_minutes(len(self.trapVs))
        #
        # def rinse_n_fire(self, threshold=None, intCallback=None, timeout=360, resV=1.5, trapV=1.5, pulses=400, delay=0.01):
        #     self.note("unbias the trap for a second")
        #     self.res.set_volt(-3)
        #     self.res.set_output(True)
        #     self.note("make sure the probe is off before the baseline")
        #     time.sleep(1)
        #
        #     self.note('firing the filament')
        #     try:
        #         self.res.set_range(10.0)
        #         self.trap.set_range(10.0)
        #     except:
        #         print "not able to set the range of the bias voltage driver. Check if it is the Yoko."
        #     self.res.set_volt(resV)
        #     self.trap.set_volt(trapV)
        #     print "now the resonator is loaded at {}V".format(self.res.get_volt())
        #     self.fil.fire_filament(pulses, delay)
        #
        #     self.note("Now wait for cooldown while taking traces")
        #     if threshold == None:
        #         threshold = 60e-3
        #     while self.fridge.get_mc_temperature() >= threshold or (time.time() - self.t0) < timeout:
        #         print '.',
        #         if intCallback != None:
        #             intCallback()
        #     self.note("fridge's cold, start sweeping...")
        #     self.note("sweep probe frequency and trap electrode")
        #
        # def get_peak(self, nwa_center=None, nwa_span=30e6, set_nwa=True, npts=320):
        #     self.na.set_trigger_source('bus')
        #     na_rf_state = self.na.get_output()
        #     self.na.set_output(True)
        #     rf_output = self.rf.get_output()
        #     self.rf.set_output(False)
        #     lo_output = self.rf.get_output()
        #     self.lo.set_output(False)
        #     if set_nwa:
        #         sweep_points = self.na.get_sweep_points()
        #         self.na.set_sweep_points(npts)
        #         if nwa_center == None:
        #             nwa_center = self.sample.freqNoE - nwa_span / 3.
        #         self.na.set_center_frequency(nwa_center)
        #         self.na.set_span(nwa_span)
        #     fpts, mags, phases = self.na.take()
        #     arg = argmax(filters.gaussian_filter1d(mags, 10))
        #     maxMag = filters.gaussian_filter1d(mags, 10)[arg]
        #     self.sample.peakF = fpts[arg]
        #     offset, amplitude, center, hvhm = fitlor(fpts, dBm_to_W(mags))
        #     print "     center via fitlor is {}, {}, {}, {}".format(offset, amplitude, center, hvhm)
        #     print "     abs(fit difference) is {}".format(abs(center - self.sample.peakF))
        #     fit_range = nwa_span / 10.
        #     print "     the good fit frequency range is {}".format(fit_range)
        #
        #     if abs(center - self.sample.peakF) <= abs(fit_range):
        #         print '     peak fitted in range'
        #         self.sample.peakF = center
        #     print "     ",
        #     self.note("peakF: {}, mag @ {}, arg @ {}".format(self.sample.peakF, maxMag, arg))
        #     self.na.set_output(na_rf_state)
        #     self.rf.set_output(rf_output)
        #     self.rf.set_output(lo_output)
        #     if set_nwa:
        #         self.na.set_sweep_points(sweep_points)
        #     print "     the peak is found at: ", self.sample.peakF
        #     return fpts, mags, phases
        #
        # def clear_plotter(self):
        #     self.plotter.clear('na spectrum')
        #     self.plotter.clear('nwa mag')
        #     self.plotter.clear('nwa phase')
        #     self.plotter.clear('nwa I')
        #     self.plotter.clear('nwa Q')
        #
        # def clear_na_plotter(self):
        #     self.plotter.clear('na spectrum')
        #
        # def clear_nwa_plotter(self):
        #     self.plotter.clear('nwa mag')
        #     self.plotter.clear('nwa phase')
        #     self.plotter.clear('nwa I')
        #     self.plotter.clear('nwa Q')
        #
        # def play_sound(self, tone=None, filename=None):
        #     sound_file_directory = r'tone_files'
        #     tone_dict = {100: '100', 250: '250', 440: '440', 1000: '1k', 10000: '10k'}
        #     if filename == None:
        #         filename = '{}Hz_44100Hz_16bit_05sec.wav'.format(tone_dict[tone])
        #     path = os.path.join(sound_file_directory, filename)
        #     winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        #
        # def stop_sound(self):
        #     sound_file_directory = r'tone_files'
        #     filename = 'Silent.wav'
        #     path = os.path.join(sound_file_directory, filename)
        #     winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        #
        # def take_spectrum(self, center=None, span=None, resbw=None):
        #     self.na.set_output(False)
        #     self.rf.set_output(True)
        #     if center == None: center = self.sample.peakF
        #     self.rf.set_frequency(center)
        #     self.sa.set_center_frequency(center)
        #     if span != None: self.sa.set_span(span)
        #     if resbw != None:
        #         self.sa.set_resbw(resbw)
        #     else:
        #         self.sa.set_resbw(self.sa.get_span() / float(self.sa.get_sweep_points()) * 2)
        #     self.sa.trigger_single()
        #
        # def save_spectrum(self, notes=None):
        #     fpts, mags = self.sa.take()  # self.sa.read_data() #
        #     self.dataCache.new_stack()
        #     self.dataCache.set('fpts', fpts)
        #     self.dataCache.set('mags', mags)
        #
        #     span = self.sa.get_span()
        #     sweep_pts = self.sa.get_sweep_points()
        #     resbw = self.sa.get_resbw()
        #     self.dataCache.set('span', span)
        #     self.dataCache.set('sweep_pts', sweep_pts)
        #     self.dataCache.set('resbw', resbw)
        #
        #     self.dataCache.note(notes)
        #     self.dataCache.set('temperature', self.fridge.get_temperature())
        #
        # def take_spectrum_group(self, note):
        #     self.take_spectrum(span=20000)
        #     self.save_spectrum(note)
        #     self.take_spectrum(span=2000)
        #     self.save_spectrum(note)
        #     self.take_spectrum(span=200)
        #     self.save_spectrum(note)


if __name__ == "__main__":
    print "main just ran but nothing is here."
