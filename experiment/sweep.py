from ehe_experiment import eHeExperiment
from setup_instruments import nwa, filament, seekat, fridge
import sweep_types

ehe = eHeExperiment(config_file_path="./jobs/trap_res_vs_power_sweep.yml")
# ehe = eHeExperiment(config_file_path="./jobs/2d_sweep_res_trap_vs_pinch_guard.yml")
# ehe = eHeExperiment(config_file_path="./jobs/default_experiment_configurations.yml")

ehe.nwa = nwa
ehe.fridge = fridge
ehe.filament = filament
ehe.seekat = seekat

ehe.nwa.configure(**vars(ehe.config.nwa.configuration or (lambda: None)))

sweeps = ehe.config.experiment.sweeps
####### experiment sweep definitions and preview logic #######
for index, sweep in enumerate(sweeps):
    sweep_type, = sweep.keys()
    sweep_params = sweep[sweep_type]
    sweep_gen = lambda: sweep_types.__dict__[sweep_type](_preview=True, **sweep_params)
    ehe.save_sweep_preview(sweep_gen(), index, title=sweep_type, blocking=ehe.config.experiment.preview_sweeps)


######## Experiment #########
ehe.note('Starting Experiment...')
ehe.note('temperature is {}K'.format(ehe.fridge.get_mc_temperature()))

if ehe.config.nwa.set_before_loading:
    for key in ehe.config.nwa.set_before_loading.keys():
        nwa.__getattribute__('set_' + key)(ehe.config.nwa.set_before_loading.__dict__[key])

if ehe.config.experiment.load_electrons:
    ehe.load_electrons()

if ehe.config.nwa.set_before_experiment:
    for key in ehe.config.nwa.set_before_experiment.keys():
        nwa.__getattribute__('set_' + key)(ehe.config.nwa.set_before_experiment.__dict__[key])

for index, sweep in enumerate(sweeps):
    sweep_type, = sweep.keys()
    sweep_params = sweep[sweep_type]
    sweep_gen = lambda: sweep_types.__dict__[sweep_type](**sweep_params)
    ####### experiment sweep definitions and preview logic #######
    print("now sweep...")

    if 'new_stack' in sweep_params and sweep_params['new_stack'] is True:
        ehe.new_stack()

    if 'set_nwa' in sweep_params and sweep_params['set_nwa']:
        for key in sweep_params['set_nwa'].keys():
            nwa.__getattribute__('set_' + key)(sweep_params['set_nwa'][key])
            ehe.dataCache.set('nwa.' + key, sweep_params['set_nwa'][key])

    ehe.sweep(sweep_gen())

if hasattr(ehe.config.nwa, 'set_before_exit'):
    for key in ehe.config.nwa.set_before_exit.keys():
        if key == 'auto_scale':
            nwa.auto_scale()
            continue
        nwa.__getattribute__('set_' + key)(ehe.config.nwa.set_before_exit.__dict__[key])
