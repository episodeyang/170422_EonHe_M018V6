from slab.instruments import FilamentDriver
from setup_instruments import seekat
import time
# Note: have to set all the voltages correct yourself
# Have tested with Res @ 3V, Trap @ 3V, All others @ 0V
for channel, volt in enumerate([3.0, 3.0, 0.0, 0.0, 0.0]):
    seekat.set_voltage(channel+1, volt)
    time.sleep(0.2)

filament = FilamentDriver(address="192.168.14.144", recv_length=2**10)
time.sleep(0.2)
filamentParams = {"amplitude": 4.2,
                  "offset": -0.5,
                  "frequency": 113e3,
                  "duration": 40e-3}
filament.setup_driver(**filamentParams)
time.sleep(0.2)
print filament.get_id()
print("Firing filament...")
filament.fire_filament(100)
print("Have a good day!")