import numpy as np


def voltage_sweep(Vguard, Vpinch, Vres_start, Vres_end, dVres, offset, **rest):
    """generator function for the voltage sweep"""
    dVres = abs(dVres) if Vres_start < Vres_end else -abs(dVres)
    Vress = np.arange(Vres_start, Vres_end + dVres, dVres)
    for k, Vres in enumerate(Vress):
        Vtrap = Vres + offset
        yield {"k": k, "Vres": Vres, "Vguard": Vguard, "Vpinch": Vpinch, "Vtrap": Vtrap}


def trap_voltage_sweep(Vres, Vguard, Vpinch, Vtrap_start, Vtrap_end, dVtrap, **rest):
    """generator function for the voltage sweep"""
    dVtrap = abs(dVtrap) if Vtrap_start < Vtrap_end else -abs(dVtrap)
    Vtraps = np.arange(Vtrap_start, Vtrap_end + dVtrap, dVtrap)
    for k, Vtrap in enumerate(Vtraps):
        yield {"k": k, "Vres": Vres, "Vguard": Vguard, "Vpinch": Vpinch, "Vtrap": Vtrap}


def sweep_2d_trap_first(Vguard, Vpinch, Vres_start, Vres_end, dVres, dVtrap, offset_limit=0.5, bi_dir=True,
                        reverse=False, **rest):
    dVres = abs(dVres) if Vres_start < Vres_end else -abs(dVres)
    Vress = np.arange(Vres_start, Vres_end + dVres, dVres)
    for Vres in Vress:
        Vtrap_start = Vres + offset_limit
        Vtrap_end = Vres - offset_limit
        if reverse:
            Vtrap_start, Vtrap_end = Vtrap_end, Vtrap_start
        for data in trap_voltage_sweep(Vres, Vguard, Vpinch, Vtrap_start, Vtrap_end, dVtrap, **rest):
            yield data
        if not bi_dir:
            continue
        for data in trap_voltage_sweep(Vres, Vguard, Vpinch, Vtrap_end, Vtrap_start, dVtrap, **rest):
            yield data
