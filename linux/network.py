#!/usr/bin/env python
from common import get_config, create_rrd
import rrdtool

CONFIG = get_config()
RRD_DATA_SOURCES = [
    "DS:in:DERIVE:120:0:U",
    "DS:out:DERIVE:120:0:U",
    "RRA:AVERAGE:0.5:1:576",
    "RRA:AVERAGE:0.5:6:672",
    "RRA:AVERAGE:0.5:24:732",
    "RRA:AVERAGE:0.5:144:1460"
]

# Loop through all network devices
for dev, name in CONFIG['network_devices'].iteritems():
    RRD = "traffic_%s.rrd" % dev
    # Create RRD file if it doesn't already exist
    create_rrd(RRD, RRD_DATA_SOURCES)

    # Get current byte count
    bytesin, bytesout = 0, 0
    try:
        bytesin = int(open('/sys/class/net/%s/statistics/rx_bytes' % dev, 'r').readlines()[0].rstrip())
        bytesout = int(open('/sys/class/net/%s/statistics/tx_bytes' % dev, 'r').readlines()[0].rstrip())
    except:
        pass

    # Update RRD values
    rrdtool.update(
        RRD,
        "-t",
        "in:out",
        "N:%s:%s" % (bytesin, bytesout)
    )

    # Create images
    for period in ["hour", "day", "week", "month", "year"]:
        rrdtool.graph(
            "traffic_%s_%s.png" % (dev, period),
            "-s -1%s" % period,
            "-t traffic on %s :: %s" % (dev, name),
            "--lazy",
            "-h", "150", "-w", "700",
            "-l 0", "-b", "1024",
            "-a", "PNG",
            "-v bytes/sec",
            "DEF:in=%s:in:AVERAGE" % RRD,
            "DEF:out=%s:out:AVERAGE" % RRD,
            "CDEF:out_neg=out,-1,*",
            "TEXTALIGN:left",
            "AREA:in#32CD32:Incoming",
            "LINE1:in#336600",
            "GPRINT:in:MAX:  Max\\: %5.1lf %s",
            "GPRINT:in:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:in:LAST: Current\\: %5.1lf %Sbytes/sec\\n",
            "AREA:out_neg#4169E1:Outgoing",
            "LINE1:out_neg#0033CC",
            "GPRINT:out:MAX:  Max\\: %5.1lf %S",
            "GPRINT:out:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:out:LAST: Current\\: %5.1lf %Sbytes/sec",
            "HRULE:0#000000"
        )
