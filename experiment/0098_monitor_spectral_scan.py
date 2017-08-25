from data_cache import dataCacheProxy
from glob import glob
import time, sys
sys.path.append(r"S:\_Data\170422 - EonHe M018V6 with L3 etch")
from modules.Common import common
from slab import dsfit, dataanalysis
from tqdm import tqdm

today = time.strftime("%y%m%d")
foldername = glob(os.path.join(r"C:\Users\slab\Desktop\Gerwin\data", today, today+"_*"))[-1]
print foldername

save = 1
f0_noE = 6.40511E9

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
    Vtrap = d.get("Vtrap")
    Vresguard = d.get("Vrg")
    Vres = d.get("Vres")
    #presweep_Vtrap = d.get('presweep_Vtrap')[0]
    temperature= d.get('temperature')
    #data_changes = (np.shape(mags)[0] != len(presweep_Vtrap))
except:
    print "Data is not in the datafile. Here's what's in the file:"
    print d.index()

def get_f0s(fpts, mags, span=2E6):
    f0s, Qs = list(), list()

    for k in tqdm(range(np.shape(mags)[0])):
        center_freq = fpts[k, np.argmax(mags[k,:])]
        try:
            fr = dsfit.fitlor(fpts[k,:], dataanalysis.dBm_to_W(mags[k,:]),
                              domain=[center_freq-span/2., center_freq+span/2.])
            f0s.append(fr[2])
            Qs.append(dataanalysis.W_to_dBm(fr[1]))#Qs.append(fr[2]/(2*fr[3]))
        except:
            print "Fit failed!"
            f0s.append(np.nan)
            Qs.append(np.nan)

    return f0s, Qs

f0s, Qs = get_f0s(fpts, mags)

startidx = np.argmin(np.diff(Vres))+1

color1 = 'maroon'; color2 = 'navy'
fig = plt.figure()
plt.title(os.path.split(filename)[1])
ax1, ax2 = common.setup_twinax(color1=color1, color2=color2)
ax1.plot(Vtrap[startidx:len(f0s)], (np.array(f0s)[startidx:]-f0_noE)/1E6, color=color1, alpha=1, lw=1)
ax2.plot(Vtrap[startidx:len(Qs)], np.array(Qs)[startidx:], '-', color=color2, alpha=1, lw=1)
ax1.set_ylabel(r"$\Delta f_0$ (MHz)")
ax2.set_ylabel(r"$Q_L$")
plt.xlim(0, np.max(Vtrap))
plt.xlabel("$V_\mathrm{trap}$")
ax1.grid()
plt.legend(loc=0, prop={'size':10})
plt.show()

plt.figure()
plt.imshow(mags, aspect='auto', interpolation='none', cmap=plt.cm.Spectral_r)
plt.colorbar()
