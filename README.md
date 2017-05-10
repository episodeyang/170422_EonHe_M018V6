# Electrons on Helium M018V6 Experiment Repo

link: https://github.com/SchusterLab/170422_EonHe_M018V6#electrons-on-helium-m018v6-experiment-repo

To start experiments
```bash
pip install -r requirements.txt
```

Each experiment is configured via a `yaml` file.

In each experiment script, you can now load the configuration directly from this `yaml` file. I have simplified both the configuration for the experiment as well as the `dataCache`.
 
For example: 

```python
from ehe_experiment import eHeExperiment
from setup_instruments import nwa, res, fridge

ehe = eHeExperiment(config_file_path="./0016_electron_loading.yml")
print ehe.config_text
ehe.note('Starting Experiment...')
ehe.nwa = nwa.configure(**vars(ehe.config.nwa.configuration))
for key in ehe.config.nwa.set.keys():
    nwa.__getattribute__('set_' + key)(ehe.config.nwa.set.__dict__[key])
```

A typical `yaml` configuration file looks like:

```yaml
prefix: sweep_2d_trap_first_long_experiment
data_directory: ..\data\{date}\{time}_{prefix}
colors:
  - "#24636c"
  - "#23aaff"
  - "#61a496"
  - "#be977d"
  - "#d85741"
instruments:
  - nwa
  - filament
  - seekat
  - fridge
# all experiment parameters goes here.
experiment:
  load_electrons: True
  loading_Vres: 3.0
  loading_Vtrap: 3.0
  loading_Vguard: 0.0
  sweeps:
#    - sweep_2d_trap_first:
#        new_stack: True
#        Vguard: 0.0 #-0.1
#        Vres_start: 3.0
#        Vres_end: 0.5
#        dVres: 0.05
#        dVtrap: 0.05
#        offset_limit: 1.0
#        reverse: False
#        bi_dir: True
    # TESTED
#    - voltage_sweep:
#        Vguard: -0.1
#        Vres_start: 3.0
#        Vres_end: -1.0
#        dVres: 0.05
#        offset: 0.5
    # TESTED
    - trap_voltage_sweep:
        Vres: 0.05
        Vguard: -0.1
        Vtrap_start: 2.0
        Vtrap_end: 0.05
        dVtrap: 0.05
#    - trap_voltage_sweep:
#        Vres: 0.05
#        Vguard: -0.1
#        Vtrap_start: 0.05
#        Vtrap_end: 2.0
#        dVtrap: 0.05

ledger:
  note_line_length: 79
# this is optional
data_cache:
fridge:
  wait_for_temp: 0.250
  min_temp_wait_time: 60
filament:
  config:
    amplitude: 4.2
    offset: -0.5
    frequency: 113e3
    duration: 40e-3
  firing:
    pulses: 100
    delay: 0.01
pulse_params:
  delay: .01
  pulses: 150
sample:
  freq_no_electron: 6.16562e9
  freq_with_e: 8023438335.47
nwa:
  model: E5071C
  # list of configuration to pass into nwa configuration method
  configuration:
    center: 6.4020e9
    span: 15e6
    # averages: 1
    sweep_points: 1601 #401
  # the rest that gets set one after another. Order is not preserved.
  set:
    format: SLOG
    measure: S21
    trigger_source: BUS
    electrical_delay: 68E-9
  load_current_configuration: True
  set_before_exit:
    format: MLOG
    auto_scale: True
    trigger_source: INT

seekat:
  res_channel: 1
  trap_channel: 2
  guard_channel: 3
```

The work enviroment would look like this:
![work_environment_screenshot](figures/work_environment_screenshot.png)


Authors:
- Ge Yang: yangge1987@gmail.com
- Gerwin Koolstra

University of Chicago