import rrdtool
import os

import simplejson
from simplejson import JSONDecodeError


def create_rrd(filename, data_sources):
    """Create RRD file if it doesn't already exist

    Parameters:
    filename - name of rrd file
    data_sources - array of rrd data definitions

    """
    if not os.path.isfile(filename):
        rrdtool.create(filename, *data_sources)


def get_config():
    """Read config file. Doesn't check for values

    Return:
    dictionary constructed from config.json

    """
    try:
        return simplejson.load(open('config.json', 'r'))
    except IOError:
        print 'Cant read config file!'
    except JSONDecodeError:
        print 'Cant parse config file!'
