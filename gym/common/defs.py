"""Identifies all the unique ids of each tool (prober and listener)
To be used by each tool initialization, 
So check gym/agent/probers/prober_*.py and check the __init__(id=)

IMPORTANT:
These IDs must be used when composing VNF-BD source files, referencing
them in proceedings for agents/monitors tools
"""

# PROBER IDS
PROBER_IPERF = 1
PROBER_PING = 2
PROBER_SIPP = 3
PROBER_IPERF3 = 4
PROBER_PKTGEN = 5
PROBER_TCPREPLAY = 6

# LISTENER IDs
LISTENER_HOST = 10
LISTENER_DOCKER = 11
LISTENER_PROCESS = 12
LISTENER_NET = 13
LISTENER_SURICATA = 14

"""Defines the map of name to IDs 
of probers and listeners.
It is used by the map of VNF-BD name of
probers/listeners.
"""
TOOLS_MAP = {
    "iperf": PROBER_IPERF,
    "ping": PROBER_PING,
    "sipp": PROBER_SIPP,
    "iperf3": PROBER_IPERF3,
    "pktgen": PROBER_PKTGEN,
    "tcpreplay": PROBER_TCPREPLAY,
    #
    "host": LISTENER_HOST,
    "docker": LISTENER_DOCKER,
    "process": LISTENER_PROCESS,
    "net": LISTENER_NET,
    "suricata": LISTENER_SURICATA,
}
