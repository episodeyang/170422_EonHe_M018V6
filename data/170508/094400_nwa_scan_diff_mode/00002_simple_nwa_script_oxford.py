from data_cache import dataCacheProxy
from slab import *
from slab.datamanagement import SlabFile
from slab.instruments import InstrumentManager, nwa
from numpy import *
import shutil, time
import msvcrt, sys
from wigglewiggle import wigglewiggle
from slab.instruments.cryostat import Triton

measurementname = 'nwa_scan_diff_mode'
datapath = r"S:\_Data\170422 - EonHe M018V6 with L3 etch\data"
scriptname = r'00002_simple_nwa_script_oxford.py'

M = wigglewiggle(measurementname, datapath, scriptname,
                 scriptpath=r"S:\_Data\170422 - EonHe M018V6 with L3 etch")
fridge = Triton(address="192.168.14.129")

print "Temperature at start of measurement is %.3f K" % (fridge.get_mc_temperature())
NWA = nwa.E5071(address="192.168.14.218")

powers = -25
averages = 1

# powers = np.array([-20])#np.arange(-25, -12.5, 2.5)
# p0 = -40 # power at which a single trace gives good enough SNR
# averages = 10 * np.log10(p0 - powers)
# averages[averages < 0] = 1
# averages[np.isnan(averages)] = 1

print(averages)

print NWA.read_data()

start = 6.437e9
stop = 6.447e9
mode = 'S21'

NWA.set_measure(mode=mode)
NWA.set_format('SLOG')
NWA.set_average_state(True)
NWA.set_averages(1)
NWA.set_start_frequency(start)
NWA.set_stop_frequency(stop)
NWA.set_ifbw(50)
NWA.set_power(powers)
NWA.set_sweep_points(1601)
NWA.set_trigger_source('BUS')

datafolder = M.create_new_datafolder(datapath, measurementname, M.today, M.timestamp)
print "Saving data in folder: %s" % os.path.join(datafolder, measurementname + '.h5')
#data_file = dataCacheProxy(expInst=measurementname, filepath=os.path.join(datafolder, measurementname + '.h5'))

time.sleep(1.0)

p = powers
a = averages
#for a, p in zip(averages, powers):
# while True:
NWA.set_power(p)
NWA.set_averages(np.int(a))
fpoints, mags, phases = NWA.take_one_averaged_trace()
print "Current time is %s : T = %.3f K" % (time.ctime(), fridge.get_mc_temperature())

with SlabFile(os.path.join(datafolder, measurementname + '.h5')) as f:
    f.append_pt('powers', p)
    f.append_pt('averages', np.int(a))
    f.append_pt('temperature', fridge.get_mc_temperature())
    f.append_line('fpoints', fpoints)
    f.append_line('mags', mags)
    f.append_line('phases', phases)

fig = plt.figure(figsize=(7.,5.))
plt.plot(fpoints, mags, 'r')

plt.xlabel("Frequency (Hz)")
plt.ylabel("$S_{21}$ magnitude (dB)")
plt.xlim(fpoints[0], fpoints[-1])
plt.grid()

fig.savefig(os.path.join(datafolder, "data_plot.png"), dpi=200)
plt.show()