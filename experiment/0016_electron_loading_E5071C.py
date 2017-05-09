from ehe_experiment import eHeExperiment

ehe = eHeExperiment(config_file_path="./0016_electron_loading.yml")
print(ehe.config)
# this should return
# Out[1]:
# {'filament_params': {'amplitude': 4.2,
#   'duration': '40e-3',
#   'frequency': '113e3',
#   'offset': -0.5},
#  'fridge_params': {'min_temp_wait_time': 60, 'wait_for_temp': 0.08},
#  'meta': {'note_line_length': 79},
#  'prefix': 'electron_loading',
#  'pulse_params': {'delay': 0.01, 'pulses': 150}}





