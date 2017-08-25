import numpy as np
import time


def sweep_all(start, end, n, delay=0, bi_dir=False, **rest):
    vs = list(np.linspace(start, end, n))
    vs = vs[:-1] + vs[::-1] if bi_dir else vs
    for k, v in enumerate(vs):
        yield {"k": k, "Vres": v, "Vtrap_guard": v, "Vres_guard": v, "Vpinch": v, "Vtrap": v}
        sleep(1, delay)


def voltage_sweep(Vguard, Vpinch, Vres_start, Vres_end, dVres, offset=0, bi_dir=False, **rest):
    """generator function for the voltage sweep"""
    dVres = abs(dVres) if Vres_start < Vres_end else -abs(dVres)
    Vress = np.arange(Vres_start, Vres_end + dVres, dVres)
    for k, Vres in enumerate(Vress):
        Vtrap = Vres + offset
        yield {"k": k, "Vres": Vres, "Vtrap_guard": Vguard, "Vres_guard": Vguard, "Vpinch": Vpinch, "Vtrap": Vtrap}
    if not bi_dir:
        return
    for k, Vres in enumerate(Vress[::-1]):
        Vtrap = Vres + offset
        yield {"k": k, "Vres": Vres, "Vtrap_guard": Vguard, "Vres_guard": Vguard, "Vpinch": Vpinch, "Vtrap": Vtrap}


def trap_voltage_sweep(Vres, Vres_guard, Vtrap_guard, Vpinch, Vtrap_start, Vtrap_end, dVtrap, bi_dir=False, **rest):
    """generator function for the voltage sweep"""
    dVtrap = abs(dVtrap) if Vtrap_start < Vtrap_end else -abs(dVtrap)
    Vtraps = np.arange(Vtrap_start, Vtrap_end + dVtrap, dVtrap)
    for k, Vtrap in enumerate(Vtraps):
        yield {"k": k, "Vres": Vres, "Vres_guard": Vres_guard, "Vtrap_guard": Vtrap_guard, "Vpinch": Vpinch, "Vtrap": Vtrap}
    if not bi_dir:
        return
    for k, Vtrap in enumerate(Vtraps[::-1]):
        yield {"k": k, "Vres": Vres, "Vres_guard": Vres_guard, "Vtrap_guard": Vtrap_guard, "Vpinch": Vpinch, "Vtrap": Vtrap}


def sweep_2d_trap_res(Vguard, Vpinch, Vres_start, Vres_end, dVres, dVtrap, offset_limit=0.5, bi_dir=True,
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


def sweep_2d_res_trap_vs_guard_pinch(Vguard_start, Vguard_end, dVguard, Vres_start, Vres_end, dVres, bi_dir=True,
                                     reverse=False, **rest):
    dVguard = abs(dVguard) if Vguard_start < Vguard_end else -abs(dVguard)
    Vguards = np.arange(Vguard_start, Vguard_end + dVguard, dVguard)
    if reverse:
        Vres_start, Vres_end = Vres_end, Vres_start
    for Vguard in Vguards:
        for data in voltage_sweep(Vguard, Vguard, Vres_start, Vres_end, dVres, **rest):
            yield data
        if not bi_dir:
            continue
        for data in voltage_sweep(Vguard, Vguard, Vres_end, Vres_start, dVres, **rest):
            yield data


def sleep(intervals=1, time_per_interval=0, preview=True, **rest):
    """this sweep type does not have any effect"""
    # notice: do you want to make this stateful or not?
    if preview or not time_per_interval or not intervals:
        return
    for i in range(intervals):
        time.sleep(time_per_interval)
