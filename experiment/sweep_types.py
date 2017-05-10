from tqdm import tqdm
import numpy as np


def voltage_sweep(Vguard, Vres_start, Vres_end, dVres, offset, **rest):
    """generator function for the voltage sweep"""
    dVres = abs(dVres) if Vres_start < Vres_end else -abs(dVres)
    Vress = np.arange(Vres_start, Vres_end + dVres, dVres)
    for k, Vres in tqdm(enumerate(Vress)):
        Vtrap = Vres + offset
        yield {"k": k, "Vres": Vres, "Vguard": Vguard, "Vtrap": Vtrap}


def trap_voltage_sweep(Vres, Vguard, Vtrap_start, Vtrap_end, dVtrap, **rest):
    """generator function for the voltage sweep"""
    dVtrap = abs(dVtrap) if Vtrap_start < Vtrap_end else -abs(dVtrap)
    Vtraps = np.arange(Vtrap_start, Vtrap_end + dVtrap, dVtrap)
    for k, Vtrap in tqdm(enumerate(Vtraps)):
        yield {"k": k, "Vres": Vres, "Vguard": Vguard, "Vtrap": Vtrap}


def sweep_2d_trap_first(Vguard, Vres_start, Vres_end, dVres, Vtrap_start, Vtrap_end, dVtrap, **rest):
    dVres = abs(dVres) if Vres_start < Vres_end else -abs(dVres)
    Vress = np.arange(Vres_start, Vres_end + dVres, dVres)
    for Vres in Vress:
        for data in trap_voltage_sweep(Vres, Vguard, Vtrap_start, Vtrap_end, dVtrap, **rest):
            yield data