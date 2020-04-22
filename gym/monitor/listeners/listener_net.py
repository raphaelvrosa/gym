import logging

from gym.monitor.listeners.listener import Listener
from gym.common.defs import LISTENER_NET

import time
from datetime import datetime
from subprocess import check_output


logger = logging.getLogger(__name__)


class ListenerNet(Listener):
    PARAMETERS = {
        'interface': 'interface',
        'duration': 'duration',
    }

    METRICS = {
        "1": 'query_size',
        "2": 'query_pkts',
        "3": 'query_drop',
        "4": 'reply_size',
        "5": 'reply_pkts',
        "6": 'reply_drop',
        "7": 'answered',
        "8": 'query_rate',
        "9": 'reply_rate',
        "10": 'query_avglen',
        "11": 'reply_avglen',
    }

    def __init__(self):
        Listener.__init__(self, id=LISTENER_NET, name='network',
                          parameters=ListenerNet.PARAMETERS,
                          metrics=ListenerNet.METRICS)
        self._command = None

    def _stats(self, interface):
        cmd = "cat /proc/net/dev | grep " + interface + " | awk '{print $2,$3,$5,$10,$11,$13}'"
        stats = check_output(['bash', '-c', cmd])
        stats_split = stats.split()
        stats_dict = {
            'query_size': float(stats_split[0]),
            'query_pkts': float(stats_split[1]),
            'query_drop': float(stats_split[2]),
            'reply_size': float(stats_split[3]),
            'reply_pkts': float(stats_split[4]),
            'reply_drop': float(stats_split[5]),
        }
        return stats_dict

    def process_diffs(self, stats_diffs, duration):
        pkt_overhead = 42
        stats_diffs_extra = {
            'answered': 100*(stats_diffs['reply_pkts']/stats_diffs['query_pkts']),
            'query_rate': stats_diffs['query_pkts'] / duration,
            'reply_rate': stats_diffs['reply_pkts'] / duration,
            'query_avglen': (stats_diffs['query_size'] / stats_diffs['query_pkts']) - pkt_overhead,
            'reply_avglen': (stats_diffs['reply_size'] / stats_diffs['reply_pkts']) - pkt_overhead,
        }
        stats_diffs.update(stats_diffs_extra)

    def options(self, options):
        opts = {}
        stop = False
        timeout = 0
        for k, v in options.items():
            if k == 'stop':
                stop = True
            if k == 'duration':
                timeout = v
            opts[k] = v

        settings = {
            "opts": opts,
            "stop": stop,
            "timeout": timeout,
        }
        return settings

    def monitor(self, opts):
        results = {}
        duration = None
        interface = None

        if 'duration' in opts:
            duration = float(opts['duration'])
        if 'interface' in opts:
            interface = opts['interface']

        if duration and interface:
            stats_before = self._stats(interface)
            time.sleep(duration)
            stats_after = self._stats(interface)
            stats_join = zip(stats_after.values(), stats_before.values())
            stats_diffs = [x-y for (x,y) in stats_join]
            stats_diff = dict(zip(stats_before.keys(), stats_diffs))
            self.process_diffs(stats_diff, duration)
            results = stats_diff

        return results

    def parser(self, out):
        metrics = []

        if out:
            for name, value in out.items():
                m = {
                    "name": name,
                    "type": "float",
                    "unit": "",
                    "scalar": value,
                }
                metrics.append(m)
        
        return metrics
        


if __name__ == '__main__':
    # opts = {
    #     'interface': 'wlx801f029aa9e7',
    #     'duration':2,
    # }

    # app = ListenerNet()
    # print(app.monitor(opts))
    
    app = ListenerNet()
    print(app.main())
