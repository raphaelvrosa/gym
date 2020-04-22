#!/usr/bin/env python
# coding=utf-8

import logging
from gym.agent.probers.prober import Prober
from gym.common.defs import PROBER_PING

logger = logging.getLogger(__name__)


class ProberPing(Prober):
    PARAMETERS = {
        'interval':'-i',
        'duration':'-w',
        'packets':'-c',
        'frame_size':'-s',
        'target':'target',
    }

    METRICS = {
        'rtt_min': 'min round-trip-time',
        'rtt_avg': 'avg round-trip-time',
        'rtt_max': 'max round-trip-time',
        'rtt_mdev': 'std dev round-trip-time',
        'frame_loss': 'frame loss ratio',
    }

    def __init__(self):
        Prober.__init__(self, id=PROBER_PING, name="ping",
                        parameters=ProberPing.PARAMETERS,
                        metrics=ProberPing.METRICS)
        self._command = 'ping'

    def options(self, options):
        opts = []
        stop = False
        timeout = 0
        for k, v in options.items():
            if k == 'target':
                continue
            else:
                opts.extend([k, v])
        if 'target' in options:
            opts.append(options['target'])
        
        settings = {
            "opts": opts,
            "stop": stop,
            "timeout": timeout
        }
        return settings

    def parser(self, out):
        _eval = {}
        lines = [line for line in out.split('\n') if line.strip()]
        
        if len(lines) > 1:
            rtt_indexes = [i for i, j in enumerate(lines) if 'rtt' in j]
        
            if not rtt_indexes:
                rtt_indexes = [i for i, j in enumerate(lines) if 'round-trip' in j]
        
            if rtt_indexes:
                rtt_index = rtt_indexes.pop()
                rtt_line = lines[rtt_index].split(' ')
                loss_line = lines[rtt_index-1].split(' ')
                rtts = rtt_line[3].split('/')
                rtt_units = rtt_line[4]
        
                if 'time' in loss_line:
                    pkt_loss = loss_line[-5][0]
                    pkt_loss_units = loss_line[-5][-1]
                else: 
                    pkt_loss = loss_line[-3][0]
                    pkt_loss_units = loss_line[-3][-1]
                
                m1 = {
                    "name": "rtt_min",
                    "type": "float",
                    "unit": rtt_units,
                    "scalar": float(rtts[0].replace(",", ".")),
                }
                
                m2 = {
                    "name": "rtt_avg",
                    "type": "float",
                    "unit": rtt_units,
                    "scalar": float(rtts[1].replace(",", ".")),
                }

                m3 = {
                    "name": "rtt_max",
                    "type": "float",
                    "unit": rtt_units,
                    "scalar": float(rtts[2].replace(",", ".")),
                }

                m4 = {
                    "name": "rtt_mdev",
                    "type": "float",
                    "unit": rtt_units,
                    "scalar": float(rtts[3].replace(",", ".")),
                }

                m5 = {
                    "name": "frame_loss",
                    "type": "float",
                    "unit": pkt_loss_units,
                    "scalar": float(pkt_loss),
                }

                _eval = [m1, m2, m3, m4, m5]

        return _eval


if __name__ == '__main__':
    app = ProberPing()
    print(app.main())