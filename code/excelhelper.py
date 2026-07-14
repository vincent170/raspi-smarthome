import math

qone = input('Rate of Change (°C/min) or Change (%/min): (a/b)')

temp1 = int(input('Starting temperature'))
temp2 = int(input('Final temperature'))
time = int(input('time taken (s)'))

if qone == 'a': #rate of change
    print((abs(temp1-temp2)*60/time))
else: #% change pm
    print((abs(temp1-temp2)/temp1*100*60/time))
