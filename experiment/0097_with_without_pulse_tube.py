from data_cache import dataCacheProxy
from time import sleep, time, strftime
from setup_instruments import fridge, nwa
sys.path.append(r"S:\_Data\170422 - EonHe M018V6 with L3 etch\modules")
from Common import common

expt = "pulse_tube_on_20mK_3seconds"

today = strftime("%y%m%d")
now = strftime("%H%M%S")
expt_path = os.path.join(r'C:\Users\slab\Desktop\Gerwin\data', today, "%s_%s_%s" % (today, now, expt))
print "Saving data in %s" % expt_path

if not os.path.isdir(expt_path):
    os.makedirs(expt_path)
sleep(1)

try:
    nwa.read_data()
except:
    pass

nwa.set_trigger_source('BUS')
nwa.set_format('SLOG')
nwa.set_average_state(True)

copyfile(os.path.join(r"C:\Users\slab\Desktop\Gerwin\experiment", this_script),
         os.path.join(expt_path, this_script))

dataCache = dataCacheProxy(file_path=os.path.join(expt_path, os.path.split(expt_path)[1] + ".h5"))

repetitions = 75
ifbw = 500
sweep_points = 1601
averages = 1
power = -40
nwa.set_ifbw(ifbw)

nwa_calibration_config = {'sweep_points': sweep_points,
                          'power': power,
                          'averages': averages,
                          'ifbw': ifbw}

nwa.configure(**nwa_calibration_config)
dataCache.set_dict('nwa_config', nwa_calibration_config)

sweep_time = nwa.get_sweep_time()
nwa.set_sweep_points(sweep_points)
sweep_times = np.linspace(0, sweep_time, sweep_points)

fft_mags = list()

for k in tqdm(range(repetitions)):
    if averages > 1:
        fpts, mags, phases = nwa.take_one_averaged_trace()
    else:
        fpts, mags, phases = nwa.take_one()

    dataCache.post("fpts", fpts)
    dataCache.post("mags", mags)
    dataCache.post("phases", phases)
    dataCache.post("sweep_times", sweep_times)

    dt = sweep_times[1]-sweep_times[0]
    n = len(phases) # length of the signal
    T = n*dt
    frq = np.arange(n)/float(T) # two sides frequency range
    frq = frq[range(n/2)] # one side frequency range

    Y = np.fft.fft(phases)/float(n) # fft computing and normalization
    Y = Y[range(n/2)] # maps the negative frequencies on the positive ones. Only works for real input signals!

    dataCache.post("fft_fpts", frq)
    dataCache.post("fft_mag", np.abs(Y)**2)

    fft_mags.append(np.abs(Y)**2)

plt.figure()
plt.title(expt)
plt.plot(frq, np.mean(np.array(fft_mags), axis=0))
plt.xlabel("FFT freq (Hz)")
plt.ylabel("Power")
plt.xscale('log')
plt.yscale('log')
