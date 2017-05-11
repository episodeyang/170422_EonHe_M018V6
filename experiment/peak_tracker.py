__author__ = 'Ge Yang'
from resonance_fitting import fit_resonance

class PeakTracker():
    def __init__(self):
        self.f0 = None
        self.fw = None
    def fit(self, fpts, mags):
        try:
            self.f0, self.fw = fit_resonance(fpts, mags)
        except:
            pass