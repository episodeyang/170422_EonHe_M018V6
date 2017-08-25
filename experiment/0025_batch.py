import numpy as np
#Vtrap_park = 0.265
#Vtrap_stop = 0.165
#print Vtrap_park

for i,j in enumerate([1]):
    if i == 0:
        do_reload_waveforms = True # Toggle this if the stored waveform has a different polarity.
        skip_presweep = False # Toggle this you don't want to set the trap to -2V and sweep up to Vtrap_park
        do_check_f0 = True # Toggle this if you want to check the resonance frequency and possibly reload electrons
    else:
        do_reload_waveforms = False
        skip_presweep=True
        do_check_f0 = False

    execfile(r"0028_electron_loading_fast_diagonal_scan_higherVres_E5071C.py")
