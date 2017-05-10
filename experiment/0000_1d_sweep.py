from ehe_experiment import eHeExperiment
from setup_instruments import nwa, filament, seekat, fridge
import sweep_types

ehe = eHeExperiment(config_file_path="./0000_1d_sweep.yml")

ehe.nwa = nwa
ehe.fridge = fridge
ehe.filament = filament
ehe.seekat = seekat

ehe.nwa.configure(**vars(ehe.config.nwa.configuration or (lambda: None)))
for key in ehe.config.nwa.set.keys():
    nwa.__getattribute__('set_' + key)(ehe.config.nwa.set.__dict__[key])

sweeps = ehe.config.experiment.sweeps
####### experiment sweep definitions and preview logic #######
for index, sweep in enumerate(sweeps):
    sweep_type, = sweep.keys()
    sweep_params = sweep[sweep_type]
    sweep_gen = lambda: sweep_types.__dict__[sweep_type](**sweep_params)
    ehe.save_sweep_preview(sweep_gen(), index, title=sweep_type, blocking=True or (index is 0))

######## Experiment #########
ehe.note('Starting Experiment...')
ehe.note('temperature is {}K'.format(ehe.fridge.get_mc_temperature()))

if ehe.config.experiment.load_electrons:
    ehe.load_electrons()

for index, sweep in enumerate(sweeps):
    sweep_type, = sweep.keys()
    sweep_params = sweep[sweep_type]
    sweep_gen = lambda: sweep_types.__dict__[sweep_type](**sweep_params)
    ####### experiment sweep definitions and preview logic #######
    print("now sweep...")
    ehe.sweep(sweep_gen())

if hasattr(ehe.config.nwa, 'set_before_exit'):
    for key in ehe.config.nwa.set_before_exit.keys():
        if key == 'auto_scale':
            nwa.auto_scale()
            continue
        nwa.__getattribute__('set_' + key)(ehe.config.nwa.set_before_exit.__dict__[key])
