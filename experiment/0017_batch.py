import numpy as np
starts =  [0.265]
stops = [0.150]

print starts

for i, start in enumerate(starts):
    if i == 0:
        do_reload_waveforms = True # Toggle this if the stored waveform has a different polarity.
        skip_presweep = False # Toggle this you don't want to set the trap to -2V and sweep up to Vtrap_park
        do_check_f0 = True # Toggle this if you want to check the resonance frequency and possibly reload electrons
    else:
        do_reload_waveforms = False
        skip_presweep=True
        do_check_f0 = False
        
    Vtrap_park = start
    Vtrap_stop = stops[i]
    execfile(r"0024_electron_loading_on_phase_slope_fast_2D_E5071C.py")
    
execfile(r"0025_batch.py")

# expt = 'determine_mu'
# execfile(r"0021_electron_loading_on_phase_slope_E5071C.py")

# expt = '2d_sweep'
# execfile(r"0021_electron_loading_on_phase_slope_E5071C.py")
