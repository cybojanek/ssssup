#!/usr/bin/env python
from common import create_rrd
import rrdtool

# TODO
# cat /sys/devices/system/node/node0/meminfo
# LOOP THROUGH ALL nodes are numa-nodeish

# RRD creation definition
RRD_DATA_SOURCES = [
    "DS:total:GAUGE:120:0:34359738368",
    "DS:free:GAUGE:120:0:34359738368",
    "DS:cached:GAUGE:120:0:34359738368",
    "RRA:AVERAGE:0.5:1:2880",
    "RRA:AVERAGE:0.5:30:672",
    "RRA:AVERAGE:0.5:120:732",
    "RRA:AVERAGE:0.5:720:1460"
]
RRD = "swap.rrd"

# Create RRD file if it doesn't already exist
create_rrd(RRD, RRD_DATA_SOURCES)

# Get current memory usage
mem = open('/proc/meminfo', 'r').readlines()

# Search for these headers
headers = ['SwapTotal', 'SwapFree', 'SwapCached']
stats = {}
for m in mem:
    header = m.split(':')[0]
    # Convert to bytes
    if header in headers:
        stats[header] = 1024 * int(m.split()[1])

# Update RRD values
rrdtool.update(
    RRD,
    "-t",
    "total:free:cached",
    "N:%s:%s:%s" % (stats['SwapTotal'], stats['SwapFree'], stats['SwapCached'])
)

# Create image
for period in ["hour", "day", "week", "month", "year"]:
    rrdtool.graph(
        "swap_%s.png" % period,
        "-s -1%s" % period,
        "-t Swap usage",
        "--lazy",
        "-h", "150", "-w", "700",
        "-l 0",
        "-b", "1024",
        "-a", "PNG",
        "-v swap usage",
        "DEF:total=%s:total:AVERAGE" % RRD,
        "DEF:free=%s:free:AVERAGE" % RRD,
        "DEF:cached=%s:cached:AVERAGE" % RRD,

        "LINE2:total#FF0000:Total",
        "GPRINT:total:MIN:    Min\\: %8.2lf %S",
        "GPRINT:total:AVERAGE:\\tAvg\\: %8.2lf %S",
        "GPRINT:total:MAX:\\tMax\\: %8.2lf %S \\n",

        "AREA:free#000099:Free",
        "GPRINT:free:MIN:     Min\\: %8.2lf %S",
        "GPRINT:free:AVERAGE:\\tAvg\\: %8.2lf %S",
        "GPRINT:free:MAX:\\tMax\\: %8.2lf %S \\n",

        "STACK:cached#32CD32:Cached",
        "GPRINT:cached:MIN:   Min\\: %8.2lf %S",
        "GPRINT:cached:AVERAGE:\\tAvg\\: %8.2lf %S",
        "GPRINT:cached:MAX:\\tMax\\: %8.2lf %S \\n",
    )

