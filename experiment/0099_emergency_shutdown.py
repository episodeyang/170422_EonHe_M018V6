from setup_instruments import fridge, seekat, yoko1, nwa, heman
from slab.instruments import BNCAWG

for k in range(8):
    try:
        seekat.set_voltage(k+1, 0.0)
    except:
        print "Could not turn off Seekat channel %d"%(k+1)

try:
    yoko1.set_output(False)
    print "Yoko1 turned off"
except:
    print "Could not turn off Yoko-1"

try:
    nwa.set_output(False)
    print "NWA output turned off"
except:
    print "Could not turn off NWA output"

for k, address in enumerate(["192.168.14.143", "192.168.14.150"]):
    try:
        vars()["bnc%d" % k] = BNCAWG(address=address)
        vars()["bnc%d" % k].set_output(False)
        print "BNC%d (%s) turned off" % (k, address)
    except:
        print "Could not turn off BNC output at %s" % address

# try:
#     heman.set_gas(False)
#     heman.set_pump(True)
#     heman.set_cryostat(True)
# except:
#     print "Pumping on helium manifold was not successful."



