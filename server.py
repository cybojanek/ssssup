import time
from sys import exit
import re
from twisted.internet import reactor
from twisted.web import static, server
from twisted.application import service, internet

from stats import get_config
from stats import Stat, CPUStat, HDDIO, HDDUsage, RAMStat, SwapStat, NetworkStat, NginxStat

# List of stats to monitor
stats = []
image_map = {}
image_gen_times = {}

PNG_MATCHER = re.compile('([\w|\-]*)_(%s)\.png' % ('|'.join(Stat.IMAGE_PERIODS)))


def update_stats(*args, **kwargs):
    """Calls itself every minute to update rrdtool stats
    """
    reactor.callLater(60.0, update_stats)
    for s in stats:
        # TODO: make this async
        s.read_stat()
        # TODO: make this async
        s.update_stat()


class DynamicStatFiles(static.File):
    """Extends static.File to dynamically make rrdtool images
    """
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    def getChild(self, path, request):
        """Overload getChild method to generate rrd images

        If a request comes in, the path is checked to match the png regex.
        If it does and its a prefix in image_map, then the last rrd image
        generation time is queried, and the image is only made if its
        been more than 60 seconds.

        """
        r = PNG_MATCHER.match(path)
        if r and r.group(1) in image_map:
            prefix, period = r.group(1), r.group(2)
            now = time.time()
            if now - image_gen_times[prefix][period] >= 60.0:
                # TODO: make this async with a callback
                image_map[prefix].make_image(prefix, period)
                image_gen_times[prefix][period] = now
        return super(self.__class__, self).getChild(path, request)


def load_stats():
    # Read config.json
    config = get_config('config.json')
    if config is None:
        exit(1)
    # Defaults
    stats.append(CPUStat(config['cpu']['physical']))
    stats.append(RAMStat())
    # Swap
    if config['swap']:
        stats.append(SwapStat())
    # Nginx
    if config['nginx'] != '':
        stats.append(NginxStat(config['nginx']))
    # Network
    for dev, name in config['network_devices'].iteritems():
        stats.append(NetworkStat(dev, name))
    # Hdd io
    for dev, name in config['hdd_io'].iteritems():
        stats.append(HDDIO(dev, name))
    # Hdd usage
    for dev, name in config['hdd_usage'].iteritems():
        stats.append(HDDUsage(dev, name))
    # Run all
    for s in stats:
        # Create rrds
        s.create_rrd()
        # Store the image prefix generators
        for prefix in s.IMAGE_PREFIXES:
            image_map[prefix] = s
            image_gen_times[prefix] = {}
            # Cache the last creation time (0)
            for period in Stat.IMAGE_PERIODS:
                image_gen_times[prefix][period] = 0

# Common code
load_stats()
# Serve http web directory
root = DynamicStatFiles("./")
# Bootstrap crontab calling
reactor.callLater(1, update_stats)

if __name__ == '__main__':  # Called directly
    reactor.listenTCP(8080, server.Site(root))
    # Run!
    reactor.run()
else:  # Invoked through twistd
    application = service.Application("SSSSUP Server")
    internet.TCPServer(8080, server.Site(root)).setServiceParent(application)
