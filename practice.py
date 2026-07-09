import math
import math


def my_abs(x):
    if x>=0:
        return x
    else:
        return -x

print(my_abs(-10))

def quadratic(a, b, c):
    x=math.pow(b,2)-4*a*c
    if x<0:
        return math.nan
    if x>0:
        fsolution=(-b+math.sqrt(x))/(2*a)
        ssolution=(-b-math.sqrt(x))/(2*a)
    return fsolution,ssolution

print(quadratic(1,-3,2))