from experiment.data_cache import dataCacheProxy
from glob import glob
import os, time
import numpy as np
from matplotlib import pyplot as plt
from slab.dataanalysis import dBm_to_W
from slab import dsfit

filepaths = glob(r"S:\_Data\170422 - EonHe M018V6 with L3 etch\data\170511\guard_pinch_hysteresis\*")

colors = ["#24636c", "#23aaff", "#61a496", "#be977d", "#d85741"]
f0_noE = 6.4054E9

for filepath in filepaths:
    # print filepath
    file = glob(os.path.join(filepath, "*.h5"))

    # print(file[0])

    d = dataCacheProxy(file[0])

    plt.figure(figsize=(10., 8.))
    plt.subplot(221)
    plt.title(os.path.split(filepath)[1])
    n = 0
    for s in d.index():

        if "stack" in s:
            print s
            mags = d.get(s + ".mags")
            fpts = d.get(s + ".fpts")

            plt.subplot(221)
            for l, V in enumerate(["Vres", "Vtrap", "Vpinch", "Vguard"]):
                vars()[V] = d.get(s + "." + V)
                plt.plot(vars()[V], '-o', lw=2.0, color=colors[l], label=V, mec='none')

            plt.legend(edgecolor='none', framealpha=1, loc=0, prop={"size" : 10})
            plt.ylabel("Electrode voltage (V)")
            f0s = list()
            for k in range(np.shape(mags)[0]):
                try:
                    center = fpts[k, np.argmax(mags[k, :])]
                    span = 5E6
                    fr = dsfit.fitlor(fpts[k, :], dBm_to_W(mags[k, :]), domain=(center - span / 2., center + span / 2.))
                    f0s.append(fr[2])
                except:
                    f0s.append(np.nan)

            plt.subplot(223)
            plt.plot(Vres, np.array(f0s), '-o', lw=2.0, mec='none', ms=3)
            plt.grid()
            plt.ylim(6.38E9, 6.41E9)
            plt.xlabel("Resonator bias voltage (V)")
            plt.ylabel("$f_0$ (Hz)")

            # if n < 2:
            #     plt.subplot("22%d"%(2*n+2))
            #     plt.imshow(mags.T, interpolation='none', aspect='auto', cmap=plt.cm.Spectral_r)
            #     #plt.ylim(6.38E9, 6.41E9)
            #     plt.xlabel("Resonator bias voltage (V)")
            #     plt.ylabel("$Frequency$ (Hz)")

            n+=1


plt.show()
