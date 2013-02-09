#!/usr/bin/env python
from common import get_config, create_rrd
import rrdtool

# RRD creation definition
# List of devices to monitor
CONFIG = get_config()
RRD_DATA_SOURCES = [
    "DS:read:DERIVE:120:0:U",
    "DS:write:DERIVE:120:0:U",
    "DS:rwait:DERIVE:120:0:U",
    "DS:wwait:DERIVE:120:0:U",
    "RRA:AVERAGE:0.5:1:576",
    "RRA:AVERAGE:0.5:6:672",
    "RRA:AVERAGE:0.5:24:732",
    "RRA:AVERAGE:0.5:144:1460"
]

for dev in CONFIG['hdd']:
    RRD = "hdd_io_%s.rrd" % dev

    # Create RRD file if it doesn't already exist
    create_rrd(RRD, RRD_DATA_SOURCES)

    # Get current byte count
    reads, writes, rwait, wwait = 0, 0, 0, 0
    try:
        values = open('/sys/block/%s/stat' % dev, 'r').readlines()[0].rstrip().split()
        reads = int(values[0])
        writes = int(values[4])
        rwait = int(values[3]) / 1000  # Seconds spent waiting for read
        wwait = int(values[7]) / 1000  # Seconds spent waiting for writes
    except:
        pass

    # Update RRD values
    rrdtool.update(
        RRD,
        "-t",
        "read:write:rwait:wwait",
        "N:%s:%s:%s:%s" % (reads, writes, rwait, wwait)
    )

    # Create image
    for period in ["hour", "day", "week", "month", "year"]:
        rrdtool.graph(
            "hdd_io_%s_%s.png" % (dev, period),
            "-s -1%s" % period,
            "-t iops on %s :: %s" % (dev, CONFIG['hdd'][dev]),
            "--lazy",
            "-h", "150", "-w", "700",
            "-l 0", "-b", "1000",
            "-a", "PNG",
            "-v iops/sec",
            "DEF:read=%s:read:AVERAGE" % RRD,
            "DEF:write=%s:write:AVERAGE" % RRD,
            "CDEF:write_neg=write,-1,*",
            "TEXTALIGN:left",
            "AREA:read#000099:Read ops ",
            "GPRINT:read:MAX:  Max\\: %5.1lf %s",
            "GPRINT:read:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:read:LAST: Current\\: %5.1lf %S ops/sec\\n",
            "AREA:write_neg#FF0000:Write ops",
            "GPRINT:write:MAX:  Max\\: %5.1lf %S",
            "GPRINT:write:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:write:LAST: Current\\: %5.1lf %S ops/sec",
            "HRULE:0#000000"
        )
        rrdtool.graph(
            "hdd_io_wait_%s_%s.png" % (dev, period),
            "-s -1%s" % period,
            "-t wait on %s :: %s" % (dev, CONFIG['hdd'][dev]),
            "--lazy",
            "-h", "150", "-w", "700",
            "-l 0", "-b", "1000",
            "-a", "PNG",
            "-v seconds",
            "DEF:rwait=%s:rwait:AVERAGE" % RRD,
            "DEF:wwait=%s:wwait:AVERAGE" % RRD,
            "CDEF:wwait_neg=wwait,-1,*",
            "TEXTALIGN:left",
            "AREA:rwait#000099:Read wait ",
            "GPRINT:rwait:MAX:  Max\\: %5.1lf %s",
            "GPRINT:rwait:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:rwait:LAST: Current\\: %5.1lf %S seconds\\n",
            "AREA:wwait_neg#FF0000:Write wait",
            "GPRINT:wwait:MAX:  Max\\: %5.1lf %S",
            "GPRINT:wwait:AVERAGE: Avg\\: %5.1lf %S",
            "GPRINT:wwait:LAST: Current\\: %5.1lf %S seconds",
            "HRULE:0#000000"
        )
