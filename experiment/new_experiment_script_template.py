import time
import numpy as np
from tqdm import tqdm

from ehe_experiment import eHeExperiment
from setup_instruments import nwa, filament, seekat, fridge

ehe = eHeExperiment(config_file_path="./0016_electron_loading_2D_sweep.yml")
print ehe.config_text
ehe.note('Starting Experiment...')

ehe.nwa = nwa
ehe.nwa.configure(**vars(ehe.config.nwa.configuration))

for key in ehe.config.nwa.set.keys():
    nwa.__getattribute__('set_' + key)(ehe.config.nwa.set.__dict__[key])

ehe.fridge = fridge
ehe.filament = filament
ehe.filament.setup_driver(**ehe.config.filament)

ehe.seekat = seekat
# ehe.set_res_voltage(0.1)

print "Starting resV sweep..."

exp_params = ehe.config.experiment

def voltage_sweep():
    """this is a generator function for the voltage sweep"""
    Vress = list(np.arange(1.0, -exp_params.dVres, -exp_params.dVres))
    for k, Vres in enumerate(Vress):
        Vtraps = list(np.arange(Vres - 0.25, Vres + 0.25, exp_params.dVtrap)) + \
                 list(np.arange(Vres + 0.25, Vres - 0.25 - exp_params.dVtrap, -exp_params.dVtrap))
        for Vtrap in Vtraps:
            yield {"k": k, "Vres": Vres, "Vtrap": Vtrap}

ehe.save_sweep_preview(voltage_sweep())
ehe.sweep(voltage_sweep())