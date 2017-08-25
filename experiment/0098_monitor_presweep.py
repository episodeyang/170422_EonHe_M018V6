from data_cache import dataCacheProxy
from glob import glob
import time, sys
sys.path.append(r"S:\_Data\170422 - EonHe M018V6 with L3 etch")
from modules.Common import common

today = time.strftime("%y%m%d")
foldername = glob(os.path.join(r"C:\Users\slab\Desktop\Gerwin\data", today, today+"_*"))[-1]
print foldername

save = 1

filename = os.path.join(foldername, os.path.split(foldername)[1]+".h5")
data_changes = 1

try:
    d = dataCacheProxy(file_path=filename)
except:
    print "Filename %s does not exist!"%filename

try:
    fpts = d.get('fpts')
    mags = d.get('mags')
    phases = d.get("phases")
    presweep_Vtrap = d.get('presweep_Vtrap')[0]
    presweep_Vres = d.get('presweep_Vres')[0]
    temperature= d.get('temperature')
    data_changes = (np.shape(mags)[0] != len(presweep_Vtrap))
except:
    print "Data is not in the datafile. Here's what's in the file:"
    print d.index()


mags_mu = np.mean(mags, axis=1)
phases_mu = np.mean(phases, axis=1)
startidx = np.argmin(np.diff(presweep_Vres))+1

color1 = 'maroon'; color2 = 'navy'
idx = 0
fig = plt.figure()
plt.title(os.path.split(filename)[1])
ax1, ax2 = common.setup_twinax(color1=color1, color2=color2)
ax1.plot(presweep_Vtrap[startidx:len(phases_mu)], phases_mu[startidx:], color=color1, alpha=1, lw=1)
ax2.plot(presweep_Vtrap[startidx:len(phases_mu)], mags_mu[startidx:], '-', color=color2, alpha=1, lw=1)
ax1.set_ylabel(r"$\varphi$ (deg)")
ax2.set_ylabel(r"$S_{21}$ (dB)")
plt.xlim(0, np.max(presweep_Vtrap))
plt.xlabel("$V_\mathrm{trap}$")
ax1.grid()
plt.legend(loc=0, prop={'size':10})
plt.show()

# plt.figure()
# plt.imshow(mags, aspect='auto', interpolation='none', cmap=plt.cm.Spectral_r)
# plt.colorbar()
