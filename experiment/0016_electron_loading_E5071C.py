from ehe_experiment import eHeExperiment
from setup_instruments import nwa, res, fridge, trap

ehe = eHeExperiment(config_file_path="./0016_electron_loading.yml")
print(ehe.config)
ehe.note('Start Experiment...')
ehe.nwa = nwa





