from kraken.core.maths import *
from kraken.core.objects.kraken_loader import KrakenLoader 
import json

if __name__ == "__main__":
    vec3 = Vec3()
    vec3.x = 3.0;
    print "vec3:" + str(vec3)
    print "length:" + str(vec3.length())
    vec3 = Vec3(1.0, 0.0, 2.0);
    print "vec3:" + str(vec3)
    print "length:" + str(vec3.length())
