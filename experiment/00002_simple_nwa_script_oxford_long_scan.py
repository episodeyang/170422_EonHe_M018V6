from data_cache import dataCacheProxy
from slab import *
from slab.datamanagement import SlabFile
from slab.instruments import InstrumentManager, nwa
from numpy import *
import shutil, time
import msvcrt, sys
from wigglewiggle import wigglewiggle
from slab.instruments.cryostat import Triton

measurementname = 'nwa_scan'
datapath = r"S:\_Data\170422 - EonHe M018V6 with L3 etch\data"
scriptname = r'00002_simple_nwa_script.py'

M = wigglewiggle(measurementname, datapath, scriptname)
fridge = Triton(address="192.168.14.129")

print "Temperature at start of measurement is %.3f K" % (fridge.get_mc_temperature())
NWA = nwa.E5071(address="192.168.14.218")

powers = 0
averages = 1

# powers = np.array([-20])#np.arange(-25, -12.5, 2.5)
# p0 = -40 # power at which a single trace gives good enough SNR
# averages = 10 * np.log10(p0 - powers)
# averages[averages < 0] = 1
# averages[np.isnan(averages)] = 1

print(averages)

print NWA.read_data()

start = 4e9
stop = 8e9
stepsize = 0.1E6
mode = 'S21'

NWA.set_measure(mode=mode)
NWA.set_format('SLOG')
NWA.set_average_state(True)
NWA.set_averages(1)
NWA.set_ifbw(1E2)
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

noof_scans = np.int(np.ceil((stop - start) / (stepsize * 1601)))

print("Taking %d scans..."%noof_scans)

for n in range(noof_scans):
    NWA.set_start_frequency(start +n  * stepsize * 1601)
    NWA.set_stop_frequency(start + (n + 1) * stepsize * 1601)

    fpoints, mags, phases = NWA.take_one_averaged_trace()
    #print "Current time is %s : T = %.3f K" % (time.ctime(), fridge.get_mc_temperature())

    if n == 0:
        fp, m, ph = fpoints, mags, phases
    if n > 0:
        fp = np.append(fp, fpoints)
        m = np.append(m, mags)
        ph = np.append(ph, phases)

    print(np.shape(fp), np.shape(m), np.shape(ph))

with SlabFile(os.path.join(datafolder, measurementname + '.h5')) as f:
    f.append_pt('powers', p)
    f.append_pt('averages', np.int(a))
    f.append_pt('temperature', fridge.get_mc_temperature())
    f.append_line('fpoints', fp)
    f.append_line('mags', m)
    f.append_line('phases', ph)

