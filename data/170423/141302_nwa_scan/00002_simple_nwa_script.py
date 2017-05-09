from data_cache import dataCacheProxy
from slab import *
from slab import common
from slab.datamanagement import SlabFile
from slab.instruments import InstrumentManager
from numpy import *
import shutil, time
import msvcrt

from wigglewiggle import wigglewiggle
from analysis import analysis

measurementname = 'nwa_scan'
datapath = r'S:\_Data\141224 - M011 Helium Channels v4\data'
scriptname = r'00002_simple_nwa_script.py'
do_fit = False

M = wigglewiggle(measurementname, datapath, scriptname)
M.initiate_instrument('na', 'NWA')
M.initiate_instrument('fridge', 'FRIDGE')
M.initiate_instrument('heman', 'heman')

center = 4.34445E9
span = 500E3

M.na_cfg['na_avgs'] = 1
M.na_cfg['na_start'] = center-span/2.
M.na_cfg['na_stop'] = center+span/2.
M.na_cfg['na_ifbw'] = 1E3
M.na_cfg['na_power'] = -10
M.na_cfg['na_sweep_pts'] = 1601

datafolder = M.create_new_datafolder(datapath, measurementname, M.today, M.timestamp)
print "Saving data in folder: %s" % datafolder
data_file = dataCacheProxy(expInst=measurementname, filepath=os.path.join(datafolder, measurementname + '.h5'))

fpoints, mags, phases = M.take_single_trace(None, M.na_cfg['na_start'], M.na_cfg['na_stop'],
                                            M.na_cfg['na_power'], M.na_cfg['na_ifbw'],
                                            M.na_cfg['na_sweep_pts'], M.na_cfg['na_avgs'], verbose=True, save=False)

#data_file.new_stack()
data_file.post('mags', mags)
data_file.post('phases', phases)
data_file.post('fpoints', fpoints)
data_file.post('temperature', M.fridge.get_mc_temperature())
data_file.post('puffs', M.heman.get_puffs())

M.save_nwa_config(data_file)

print "\tFinished saving data to %s" % data_file

if do_fit:
    fitres = dsfit.fitlor(fpoints, dataanalysis.dBm_to_W(mags), showfit = False)
    fig = plt.figure(figsize = (6.,4.))
    common.configure_axes(11)
    plt.plot(fpoints, dataanalysis.dBm_to_W(mags), '.k')
    plt.plot(fpoints, dsfit.lorfunc(fitres, fpoints), '-r', lw = 2.0)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('$|S_{21}|^2$')
    fig.savefig(os.path.join(datafolder, 'magnitude_fit.png'))

    fig2 = plt.figure(figsize = (6.,4.))
    common.configure_axes(11)
    plt.plot(fpoints, phases, '.k')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel(r'$\angle S_{21}$')
    fig2.savefig(os.path.join(datafolder, 'phase.png'))

    plt.show()