from matplotlib import pyplot as plt
import numpy as np
from pylab import *
import time

ion()

tstart = time.time()               # for profiling
x = arange(0,2*pi,0.01)            # x-array
line, = plot(x,sin(x))
for i in arange(1,5):
    line.set_ydata(sin(x+i/10.0))  # update the data
    draw()                         # redraw the canvas
    time.sleep(1)

print 'FPS:' , 200/(time.time()-tstart)