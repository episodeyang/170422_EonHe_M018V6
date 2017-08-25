from time import sleep
from setup_instruments import nwa
from resonance_fitting import fit_res_gerwin
from slab.instruments import BNCAWG, BiasDriver
import numpy as np
from tqdm import tqdm

from quicktimetrace import bnc, run, set_bnc_offset

# bnc = BiasDriver(address="192.168.14.143")#BNCAWG(address="192.168.14.143")
# trigger = BNCAWG(address="192.168.14.149")

# bnc.setup_volt_source(duration=None, pulse_voltage=None, rest_voltage=None, autorange='off')

if __name__ == '__main__':
    dV = 0.05
    vpts = np.arange(0.00, -0.50-dV, -dV)
    set_bnc_offset(1E-3)
    # bnc.set_function('DC')
    for v in vpts:
        set_bnc_offset(v)
        sleep(1.0)

    # bnc.socket.close()
    # trigger.socket.close()
    sleep(0.5)

    # bnc = BiasDriver(address="192.168.14.143")
    # bnc.set_function('ARB')
    # bnc.setup_volt_source(duration=None, pulse_voltage=None, rest_voltage=None, autorange='off')


    # from quicktimetrace import run
    run(v, v+0.250)
    # set_bnc_offset(1E-3)