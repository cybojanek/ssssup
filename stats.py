import os
import rrdtool
import simplejson
import urllib2


def get_config(file_path):
    """Read config file. Doesn't check for values

    Return:
    dictionary constructed from config.json

    """
    try:
        return simplejson.load(open(file_path, 'r'))
    except IOError:
        print 'Cant read config file!'
        return None
    except simplejson.JSONDecodeError:
        print 'Cant parse config file!'
        return None


class DS(object):
    GAUGE, DERIVE = "GAUGE", "DERIVE"
    AVERAGE, MINIMUM, MAXIMUM, LAST = "AVERAGE", "MINIMUM", "MAXIMUM", "LAST"

    @staticmethod
    def ds(names=None, dstype=None, interval=120, llimit=0, ulimit="U"):
        """Return a list of rrdtool DS strings

        Keyword Arguments:
        names - list of string names for sources
        dstype - one of DS.GAUGE or DS.DERIVE
        interval - stat timeout, default: 120
        llimit - lower limit on data, default: 0
        ulimit - upper limit on data, default: "U"

        Return:
        list of DS strings

        """
        ret = []
        for name in names:
            if dstype not in [DS.GAUGE, DS.DERIVE]:
                raise ValueError("Need a data string dstype")
            if not isinstance(ulimit, int) and not ulimit == "U":
                raise ValueError("Need a valid data string ulimit")
            ret.append("DS:%s:%s:%s:%s:%s" % (name, dstype, interval, llimit,
                                              ulimit))
        return ret

    @staticmethod
    def rra(cf=None, steps=None, rows=None):
        """Return a list of rrdtool RRA strings
        Number of steps must equal number of rows

        Keyword Arguments:
        cf - one of DS.AVERAGE, DS.MINIMUM, DS.MAXIMUM, DS.LAST
        steps - lists of steps
        rows - list of rows

        Return:
        list of RRA strings

        """
        ret = []
        for step, row in zip(steps, rows):
            if cf not in [DS.AVERAGE, DS.MINIMUM, DS.MAXIMUM, DS.LAST]:
                raise ValueError("Need a proper cf value")
            if not isinstance(step, int):
                raise ValueError("Step needs to be an int")
            if not isinstance(row, int):
                raise ValueError("Row needs to be an int")
            ret.append("RRA:%s:0.5:%s:%s" % (cf, step, row))
        return ret


class Stat(object):
    """Generic stat collection class.
    Must implement read and write data
    TODO: abstract rrd data sources
    TODO: subprocess calls for rrdtool in twisted for async
    """
    AVERAGES = DS.rra(DS.AVERAGE, [1, 30, 120, 720], [2880, 672, 732, 1460])
    IMAGE_PREFIXES = []
    IMAGE_PERIODS = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, file_name, rrd_data_source, averages=None):
        self.rrd_file_name = file_name
        self.rrd_data_source = rrd_data_source
        if averages is None:
            self.averages = Stat.AVERAGES
        else:
            self.averages = averages
        self.stats = {}

    def create_rrd(self):
        """Create RRD file if it doesn't already exist
        Uses:
        self.rrd_file_name - name of rrd file
        self.rrd_data_source - array of rrd data definitions

        """
        # TODO: check for matching data sources
        if not os.path.isfile(self.rrd_file_name):
            rrdtool.create(self.rrd_file_name, *self.rrd_data_source + self.averages)

    def update_stat(self):
        """Update RRD file with key value pairs from self.stats
        Uses:
        self.stats

        """
        # TODO: check for matching data sources
        # Update RRD values
        rrdtool.update(
            self.rrd_file_name,
            "-t",
            ":".join(self.stats.keys()),
            "N:%s" % (":".join([str(self.stats[x]) for x in self.stats]))
        )

    def read_stat(self):
        raise NotImplemented("Read Stat not implemented")

    def make_image(self, prefix, period):
        if prefix not in self.IMAGE_PREFIXES:
            raise Exception("Prefix: %s not in image prefixes" % (prefix))
        if period not in self.IMAGE_PERIODS:
            raise Exception("Period: %s not in image periods" % (period))


class CPUStat(Stat):
    """Collect CPU usage information
    """
    FILE_NAME = 'cpu.rrd'
    RRD_DATA_SOURCES = DS.ds(["user", "nice", "system", "idle", "wait"],
                             DS.DERIVE)
    IMAGE_PREFIXES = ['cpu']

    def __init__(self, pcpu):
        """
        Arguments:
        pcpu - number of physical cpus

        """
        super(CPUStat, self).__init__(CPUStat.FILE_NAME,
                                      CPUStat.RRD_DATA_SOURCES)
        self.pcpu = pcpu
        self.stats['user'] = 0
        self.stats['nice'] = 0
        self.stats['system'] = 0
        self.stats['idle'] = 0
        self.stats['wait'] = 0

    def read_stat(self):
        stats = [int(x) for x in open("/proc/stat", 'r').readline().split()[1:6]]
        self.stats['user'] = stats[0]
        self.stats['nice'] = stats[1]
        self.stats['system'] = stats[2]
        self.stats['idle'] = stats[3]
        self.stats['wait'] = stats[4]

    def make_image(self, prefix, period):
        super(CPUStat, self).make_image(prefix, period)
        rrdtool.graph(
            "%s_%s.png" % (prefix, period),
            "-s -1%s" % period,
            "-t Cpu usage",
            "--lazy",
            "-h", "300", "-w", "700", "--full-size-mode",
            "-r",
            "-l 0",
            "-a", "PNG",
            "-v cpu usage",
            "DEF:user=%s:user:AVERAGE" % CPUStat.FILE_NAME,
            "DEF:nice=%s:nice:AVERAGE" % CPUStat.FILE_NAME,
            "DEF:system=%s:system:AVERAGE" % CPUStat.FILE_NAME,
            "DEF:idle=%s:idle:AVERAGE" % CPUStat.FILE_NAME,
            "DEF:wait=%s:wait:AVERAGE" % CPUStat.FILE_NAME,

            "AREA:user#FF0000:User",
            "GPRINT:user:MIN:    Min\\: %10.0lf ",
            "GPRINT:user:AVERAGE:\\tAvg\\: %10.0lf ",
            "GPRINT:user:MAX:\\tMax\\: %10.0lf \\n",

            "STACK:nice#000099:Nice",
            "GPRINT:nice:MIN:    Min\\: %10.0lf ",
            "GPRINT:nice:AVERAGE:\\tAvg\\: %10.0lf ",
            "GPRINT:nice:MAX:\\tMax\\: %10.0lf \\n",

            "STACK:system#FFFF00:System",
            "GPRINT:system:MIN:  Min\\: %10.0lf ",
            "GPRINT:system:AVERAGE:\\tAvg\\: %10.0lf ",
            "GPRINT:system:MAX:\\tMax\\: %10.0lf \\n",

            "STACK:idle#32CD32:Idle",
            "GPRINT:idle:MIN:    Min\\: %10.0lf ",
            "GPRINT:idle:AVERAGE:\\tAvg\\: %10.0lf ",
            "GPRINT:idle:MAX:\\tMax\\: %10.0lf \\n",

            "STACK:wait#ff9c0f:Wait",
            "GPRINT:wait:MIN:    Min\\: %10.0lf ",
            "GPRINT:wait:AVERAGE:\\tAvg\\: %10.0lf ",
            "GPRINT:wait:MAX:\\tMax\\: %10.0lf \\n",
            "HRULE:0#000000",
            # Draw a line across the max for what max usage should be
            # this is particularly usefull if you have hyperthreading
            # or if you change processor count
            "HRULE:%s#000000:Max Usage" % (self.pcpu * 100),
        )


class HDDStat(Stat):
    """Collect RAM usage information
    """
    FILE_NAME = 'hdd_io_%s.rrd'
    RRD_DATA_SOURCES = DS.ds(["read", "write", "rwait", "wwait"], DS.DERIVE)

    def __init__(self, device, name):
        """
        Arguments:
        device - device name
        name - human name of device

        """
        super(HDDStat, self).__init__(HDDStat.FILE_NAME % device,
                                      HDDStat.RRD_DATA_SOURCES)
        self.device = device
        self.name = name
        self.stats['read'] = 0
        self.stats['write'] = 0
        self.stats['rwait'] = 0
        self.stats['wwait'] = 0
        self.IMAGE_PREFIXES = ['hdd_io_%s' % self.device, 'hdd_io_wait_%s' % self.device]

    def read_stat(self):
        self.stats['read'] = 0
        self.stats['write'] = 0
        self.stats['rwait'] = 0
        self.stats['wwait'] = 0
        try:
            values = open('/sys/block/%s/stat' % self.device, 'r').readlines()
            values = values[0].rstrip().split()
            self.stats['read'] = int(values[0])
            self.stats['write'] = int(values[4])
            # Seconds spent waiting for read
            self.stats['rwait'] = int(values[3]) / 1000
            # Seconds spent waiting for writes
            self.stats['wwait'] = int(values[7]) / 1000
        except:
            pass

    def make_image(self, prefix, period):
        super(HDDStat, self).make_image(prefix, period)
        if prefix == 'hdd_io_%s' % self.device:
            rrdtool.graph(
                "hdd_io_%s_%s.png" % (self.device, period),
                "-s -1%s" % period,
                "-t iops on %s :: %s" % (self.device, self.name),
                "--lazy",
                "-h", "300", "-w", "700", "--full-size-mode",
                "-l 0", "-b", "1000",
                "-a", "PNG",
                "-v iops/sec",
                "DEF:read=%s:read:AVERAGE" % HDDStat.FILE_NAME % self.device,
                "DEF:write=%s:write:AVERAGE" % HDDStat.FILE_NAME % self.device,
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
        elif prefix == 'hdd_io_wait_%s' % self.device:
            rrdtool.graph(
                "hdd_io_wait_%s_%s.png" % (self.device, period),
                "-s -1%s" % period,
                "-t wait on %s :: %s" % (self.device, self.name),
                "--lazy",
                "-h", "300", "-w", "700", "--full-size-mode",
                "-l 0", "-b", "1000",
                "-a", "PNG",
                "-v seconds",
                "DEF:rwait=%s:rwait:AVERAGE" % HDDStat.FILE_NAME % self.device,
                "DEF:wwait=%s:wwait:AVERAGE" % HDDStat.FILE_NAME % self.device,
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


class RAMStat(Stat):
    """Collect RAM usage information
    """
    FILE_NAME = 'ram.rrd'
    RRD_DATA_SOURCES = DS.ds(["total", "free", "buffers", "cached"], DS.GAUGE,
                             ulimit=34359738368)
    IMAGE_PREFIXES = ['ram']

    def __init__(self):
        super(RAMStat, self).__init__(RAMStat.FILE_NAME,
                                      RAMStat.RRD_DATA_SOURCES)
        self.stats['total'] = 0
        self.stats['free'] = 0
        self.stats['buffers'] = 0
        self.stats['cached'] = 0

    def read_stat(self):
        # Get current memory usage
        mem = open('/proc/meminfo', 'r').readlines()

        # Search for these headers
        headers = ['MemTotal', 'MemFree', 'Buffers', 'Cached']
        stats = {}
        for m in mem:
            header = m.split(':')[0]
            # Convert to bytes
            if header in headers:
                stats[header] = 1024 * int(m.split()[1])
        self.stats['total'] = stats['MemTotal']
        self.stats['free'] = stats['MemFree']
        self.stats['buffers'] = stats['Buffers']
        self.stats['cached'] = stats['Cached']

    def make_image(self, prefix, period):
        super(RAMStat, self).make_image(prefix, period)
        rrdtool.graph(
            "%s_%s.png" % (prefix, period),
            "-s -1%s" % period,
            "-t Memory usage",
            "--lazy",
            "-h", "300", "-w", "700", "--full-size-mode",
            "-l 0",
            "-b", "1024",
            "-a", "PNG",
            "-v mem usage",
            "DEF:total=%s:total:AVERAGE" % RAMStat.FILE_NAME,
            "DEF:free=%s:free:AVERAGE" % RAMStat.FILE_NAME,
            "DEF:buffers=%s:buffers:AVERAGE" % RAMStat.FILE_NAME,
            "DEF:cached=%s:cached:AVERAGE" % RAMStat.FILE_NAME,
            "CDEF:used=total,free,-,buffers,-,cached,-",

            "LINE2:total#FF0000:Total",
            "GPRINT:total:MIN:    Min\\: %8.2lf %S",
            "GPRINT:total:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:total:MAX:\\tMax\\: %8.2lf %S \\n",

            "AREA:free#000099:Free",
            "GPRINT:free:MIN:     Min\\: %8.2lf %S",
            "GPRINT:free:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:free:MAX:\\tMax\\: %8.2lf %S \\n",

            "STACK:buffers#FFFF00:Buffers",
            "GPRINT:buffers:MIN:  Min\\: %8.2lf %S",
            "GPRINT:buffers:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:buffers:MAX:\\tMax\\: %8.2lf %S \\n",

            "STACK:cached#32CD32:Cached",
            "GPRINT:cached:MIN:   Min\\: %8.2lf %S",
            "GPRINT:cached:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:cached:MAX:\\tMax\\: %8.2lf %S \\n",

            "STACK:used#FF9C0F:Used",
            "GPRINT:used:MIN:     Min\\: %8.2lf %S",
            "GPRINT:used:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:used:MAX:\\tMax\\: %8.2lf %S \\n",
        )


class SwapStat(Stat):
    """Collect swap usage information
    """
    FILE_NAME = 'swap.rrd'
    RRD_DATA_SOURCES = DS.ds(["total", "free", "cached"], DS.GAUGE,
                             ulimit=34359738368)
    IMAGE_PREFIXES = ['swap']

    def __init__(self):
        super(SwapStat, self).__init__(SwapStat.FILE_NAME,
                                       SwapStat.RRD_DATA_SOURCES)
        self.stats['total'] = 0
        self.stats['free'] = 0
        self.stats['cached'] = 0

    def read_stat(self):
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
        self.stats['total'] = stats['SwapTotal']
        self.stats['free'] = stats['SwapFree']
        self.stats['cached'] = stats['SwapCached']

    def make_image(self, prefix, period):
        super(SwapStat, self).make_image(prefix, period)
        rrdtool.graph(
            "%s_%s.png" % (prefix, period),
            "-s -1%s" % period,
            "-t Swap usage",
            "--lazy",
            "-h", "300", "-w", "700", "--full-size-mode",
            "-l 0",
            "-b", "1024",
            "-a", "PNG",
            "-v swap usage",
            "DEF:total=%s:total:AVERAGE" % SwapStat.FILE_NAME,
            "DEF:free=%s:free:AVERAGE" % SwapStat.FILE_NAME,
            "DEF:cached=%s:cached:AVERAGE" % SwapStat.FILE_NAME,
            "CDEF:used=total,free,-,cached,-",

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

            "STACK:used#FF9C0F:Used",
            "GPRINT:used:MIN:     Min\\: %8.2lf %S",
            "GPRINT:used:AVERAGE:\\tAvg\\: %8.2lf %S",
            "GPRINT:used:MAX:\\tMax\\: %8.2lf %S \\n"
        )


class NetworkStat(Stat):
    """Collect RAM usage information
    """
    FILE_NAME = 'traffic_%s.rrd'
    RRD_DATA_SOURCES = DS.ds(["in", "out"], DS.DERIVE)

    def __init__(self, device, name):
        """
        Arguments:
        device - device name
        name - human name of device

        """
        super(NetworkStat, self).__init__(NetworkStat.FILE_NAME % device,
                                          NetworkStat.RRD_DATA_SOURCES)
        self.device = device
        self.name = name
        self.stats['in'] = 0
        self.stats['out'] = 0
        self.IMAGE_PREFIXES = ['traffic_%s' % (self.device)]

    def read_stat(self):
        # Get current byte count
        self.stats['in'] = 0
        self.stats['out'] = 0
        try:
            self.stats['in'] = int(open('/sys/class/net/%s/statistics/rx_bytes' % self.device, 'r').readlines()[0].rstrip())
            self.stats['out'] = int(open('/sys/class/net/%s/statistics/tx_bytes' % self.device, 'r').readlines()[0].rstrip())
        except:
            pass

    def make_image(self, prefix, period):
        super(NetworkStat, self).make_image(prefix, period)
        rrdtool.graph(
            "%s_%s.png" % (prefix, period),
            "-s -1%s" % period,
            "-t traffic on %s :: %s" % (self.device, self.name),
            "--lazy",
            "-h", "300", "-w", "700", "--full-size-mode",
            "-l 0", "-b", "1024",
            "-a", "PNG",
            "-v bytes/sec",
            "DEF:in=%s:in:AVERAGE" % NetworkStat.FILE_NAME % self.device,
            "DEF:out=%s:out:AVERAGE" % NetworkStat.FILE_NAME % self.device,
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


class NginxStat(Stat):
    """Collect Nginx usage information
    """
    FILE_NAME = 'nginx.rrd'
    RRD_DATA_SOURCES = DS.ds(["requests"], DS.DERIVE) + \
        DS.ds(["total", "reading", "writing", "waiting"], DS.GAUGE)
    IMAGE_PREFIXES = ['nginx_requests', 'nginx_connections']

    def __init__(self, url):
        super(NginxStat, self).__init__(NginxStat.FILE_NAME,
                                        NginxStat.RRD_DATA_SOURCES)
        self.url = url
        self.stats['requests'] = 0
        self.stats['total'] = 0
        self.stats['reading'] = 0
        self.stats['writing'] = 0
        self.stats['waiting'] = 0

    def read_stat(self):
        # Ask nginx for current stats
        text = urllib2.urlopen(self.url).readlines()
        self.stats['requests'] = int(text[2].rstrip().split()[2])
        self.stats['total'] = int(text[0].rstrip().split(':')[1])
        rww = [int(x) for x in text[3].rstrip().split() if x.isdigit()]
        self.stats['reading'] = rww[0]
        self.stats['writing'] = rww[1]
        self.stats['waiting'] = rww[2]

    def make_image(self, prefix, period):
        super(NginxStat, self).make_image(prefix, period)
        if prefix == 'nginx_requests':
            rrdtool.graph(
                "nginx_requests_%s.png" % period,
                "-s -1%s" % period,
                "-t Requests on nginx",
                "--lazy",
                "-h", "300", "-w", "700", "--full-size-mode",
                "-l 0",
                "-a", "PNG",
                "-v requests/sec",
                "DEF:requests=%s:requests:AVERAGE" % NginxStat.FILE_NAME,
                "AREA:requests#336600:Requests",
                "GPRINT:requests:MAX:Max\\: %5.1lf %S",
                "GPRINT:requests:AVERAGE:\\tAvg\\: %5.1lf %S",
                "GPRINT:requests:LAST:\\tCurrent\\: %5.1lf %S",
                "HRULE:0#000000"
            )
        elif prefix == 'nginx_connections':
            rrdtool.graph(
                "nginx_connections_%s.png" % period,
                "-s -1%s" % period,
                "-t Requests on nginx",
                "--lazy",
                "-h", "300", "-w", "700", "--full-size-mode",
                "-l 0",
                "-a", "PNG",
                "-v requests",
                "DEF:total=%s:total:AVERAGE" % NginxStat.FILE_NAME,
                "DEF:reading=%s:reading:AVERAGE" % NginxStat.FILE_NAME,
                "DEF:writing=%s:writing:AVERAGE" % NginxStat.FILE_NAME,
                "DEF:waiting=%s:waiting:AVERAGE" % NginxStat.FILE_NAME,

                "LINE2:total#22FF22:Total",
                "GPRINT:total:LAST:   Current\\: %5.1lf %S",
                "GPRINT:total:MIN:  Min\\: %5.1lf %S",
                "GPRINT:total:AVERAGE: Avg\\: %5.1lf %S",
                "GPRINT:total:MAX:  Max\\: %5.1lf %S\\n",

                "AREA:reading#0022FF:Reading",
                "GPRINT:reading:LAST: Current\\: %5.1lf %S",
                "GPRINT:reading:MIN:  Min\\: %5.1lf %S",
                "GPRINT:reading:AVERAGE: Avg\\: %5.1lf %S",
                "GPRINT:reading:MAX:  Max\\: %5.1lf %S\\n",

                "STACK:writing#FF0000:Writing",
                "GPRINT:writing:LAST: Current\\: %5.1lf %S",
                "GPRINT:writing:MIN:  Min\\: %5.1lf %S",
                "GPRINT:writing:AVERAGE: Avg\\: %5.1lf %S",
                "GPRINT:writing:MAX:  Max\\: %5.1lf %S\\n",

                "STACK:waiting#00AAAA:Waiting",
                "GPRINT:waiting:LAST: Current\\: %5.1lf %S",
                "GPRINT:waiting:MIN:  Min\\: %5.1lf %S",
                "GPRINT:waiting:AVERAGE: Avg\\: %5.1lf %S",
                "GPRINT:waiting:MAX:  Max\\: %5.1lf %S\\n",
                "HRULE:0#000000"
            )


class RedisStat(Stat):
    """Collect Redis usage information
    """
    FILE_NAME = 'redis.rrd'
    RRD_DATA_SOURCES = DS.ds(["total_commands_processed"], DS.DERIVE) + \
        DS.ds(["used_memory", "rdb_changes_since_last_save", "keys"], DS.GAUGE)

    def __init__(self):
        super(RedisStat, self).__init__(RedisStat.FILE_NAME, RedisStat.DATA_SOURCES)
        self.stats['used_memory'] = 0
        self.stats['rdb_changes_since_last_save'] = 0
        self.stats['total_commands_processed'] = 0
        # sum(db1, db2)....
        self.stats['keys'] = 0
        self.redis = redis.StrictRedis()

    def read_stat(self):
        rs = self.redis.info()
        for x in ['connected_clients', 'used_memory', 'used_memory_lua',
                  'rdb_changes_since_last_save', 'total_commands_processed',
                  'keyspace_hits', 'keyspace_misses']:
            redis.stats[x] = rs[x]
        self.stats['keys'] = sum([rs[db]['keys'] for db in
                                  filter(lambda x: x.startswith('db'),
                                         rs.keys())])

    def make_image(self, period):
        pass
