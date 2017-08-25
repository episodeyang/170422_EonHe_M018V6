__author__ = 'Ge Yang'
from slab import dataanalysis, fitlor
from slab.dsfit import lorfunc

#lorfun
#dBm_to_W
#W_to_dBm
import numpy as np

def fit_res_gerwin(fpts, mags, span=3E6):
    "return f0, Q"
    center_freq = fpts[np.argmax(mags)]
    try:
        fr = fitlor(fpts, dataanalysis.dBm_to_W(mags), domain=(center_freq - span / 2., center_freq + span / 2.))
        return fr[2], fr[2]/(2*fr[3])
    except:
        print "Fit failed!"
        return center_freq, 0.0

def fit_resonance(fpts, mags):
    "return f0, fw <= width at half maximum."
    center_freq = fpts[np.argmax(mags)]
    span = 5E6
    fr = fitlor(fpts, dataanalysis.dBm_to_W(mags), domain=(center_freq - span / 2., center_freq + span / 2.))
    return fr[2:]


import matplotlib.pyplot as plt

if __name__ == "__main__":
    # first test if W_to_dBm is inverse of dBm_to_W
    fpts = np.linspace(6e9, 6.005e9, 1601)
    p = [0, 1, 6.0025e9, 0.2e6]
    ws = lorfunc(p, fpts)
    mags = dataanalysis.W_to_dBm(ws)
    plt.subplot(311)
    plt.plot(fpts, ws)
    plt.subplot(312)
    plt.plot(fpts, dataanalysis.dBm_to_W(mags), color='red', alpha=0.3, linewidth=5)

    plt.subplot(313)
    plt.plot(fpts, mags)
    f0, fw = fit_resonance(fpts, mags)
    print("fitting parameters f0={}, whm={}".format(f0, fw))
    plt.plot(fpts, dataanalysis.W_to_dBm(lorfunc([0, 1] + [f0, fw], fpts)), color='red', alpha=0.3, linewidth=5)
    plt.show()
