from ehe_experiment import eHeExperiment
from setup_instruments import nwa, res, fridge

ehe = eHeExperiment(config_file_path="./0016_electron_loading.yml")
print(ehe.config)
ehe.note('Start Experiment...')
ehe.nwa = nwa.configure(**vars(ehe.config.nwa.configuration))
for key in ehe.config.nwa.set.keys():
    nwa.__getattribute__('set_' + key)(ehe.config.nwa.set.__dict__[key])
