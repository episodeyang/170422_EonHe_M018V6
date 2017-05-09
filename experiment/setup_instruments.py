from slab.instruments import InstrumentManager, HeliumManifold, FilamentDriver, BNCAWG
from slab.instruments.PNAX import N5242A
from slab.instruments.cryostat import Triton
from slab.instruments.nwa import E5071
from slab.instruments.Seekat import Seekat
#from TeensyTemp import TeensyTemp

im = InstrumentManager()

#guard = YokogawaGS200(address="192.168.14.146")#im['SRS']
#res = YokogawaGS200(address="192.168.14.146")
#srs = im['SRS']
#trap = YokogawaGS200(address="192.168.14.148")

heman = HeliumManifold(address="http://192.168.14.22")#im['heman']
res = Seekat.Seekat(address="COM11")
#fridge = im['FRIDGE']
#heman = HeliumManifold(address="http://192.168.14.22")
filament = FilamentDriver(address="192.168.14.144", recv_length=2**10)
#nwa = N5242A("N5242A", address="192.168.14.249")
nwa = E5071(address="192.168.14.218")
fridge = Triton(address='192.168.14.129')
#bnc = BNCAWG(address="192.168.14.143")
#trigger = BNCAWG(address="192.168.14.229")

#teensy = TeensyTemp(name="", address="COM12", enabled=True, timeout=0.25, baudrate=115200)
#print teensy.get_id()
#teensy.toggle_led()

# def test_srs(srs_instance):
#     output = list()
#     for k in range(4):
#         output.append(srs_instance.get_volt(channel=k+1))
#     output_str = "\tch1: %.3f V\n\tch2: %.3f V\n\tch3: %.3f V\n\tch4: %.3f V"%(output[0], output[1], output[2], output[3])
#     return output_str
#
# def test_yoko(yoko_instance):
#     answer = yoko_instance.get_volt()
#     return "Yoko output is %.3f V"%answer
#
# def test_nwa():
#     output = 'ON' if nwa.get_output() else 'OFF'
#     return "PNAX output is %s" % output
#
# def test_heman():
#     return heman.get_manifold_status()
#
# def test_filament():
#     output = 'ON' if filament.get_output() else 'OFF'
#     return "Filament output is %s" % output
#
# def test_fridge():
#     answer = fridge.get_temperature()
#     return "Current temperature at base plate is %.3f K" % answer
#
# if __name__ == '__main__':
#     print "Testing heman..."
#     print '\t',test_heman()
#
#     print "Testing filament..."
#     print '\t',test_filament()
#
#     print "Testing NWA..."
#     print '\t',test_nwa()
#
#     print "Testing fridge..."
#     print '\t',test_fridge()
#
#     print "Testing SRS..."
#     print  test_srs(guard)
#
#     print "Testing Yoko @ 192.168.14.148..."
#     print '\t',test_yoko(res)
#
#     print "Testing Yoko @ 192.168.14.146..."
#     print '\t',test_yoko(trap)