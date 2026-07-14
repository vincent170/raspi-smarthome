import math


temp1 = float(input('Starting temperature'))
temp2 = float(input('Final temperature'))
time = int(input('time taken (s)'))

print(f'Rate of change (C/min): {(abs(temp1-temp2)*60/time)}')
print(f'Rate of change (%/min): {(abs(temp1-temp2)/temp1*100*60/time)}')