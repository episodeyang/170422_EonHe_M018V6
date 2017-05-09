from data_cache import dataCacheProxy
from slab import *
from slab.datamanagement import SlabFile
from slab.instruments import InstrumentManager, nwa
from numpy import *
import shutil, time
import msvcrt, sys
from wigglewiggle import wigglewiggle
from slab.instruments.cryostat import Triton
from matplotlib import pyplot as plt

filename = r"S:\_Data\170422 - EonHe M018V6 with L3 etch\data\170423\145018_nwa_scan\nwa_scan.h5"
f = SlabFile(filename)

fpoints = f.get("fpoints")[0]
mags = f.get("mags")[0]

fig = plt.figure(figsize=(15.,5.))
plt.plot(fpoints, mags)

plt.xlabel("Frequency (Hz)")
plt.ylabel("$S_{21}$ magnitude (dB)")
plt.xlim(fpoints[0], fpoints[-1])
plt.grid()

#fig.savefig(os.path.join(os.path.split(filename)[0], "nwa_scan.png"), dpi=200)
plt.show()
f.close()