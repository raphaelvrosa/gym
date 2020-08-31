import os
import logging
import json
from gym.common.defs import PROBER_PKTGEN
from gym.agent.probers.prober import Prober

logger = logging.getLogger()


class ProberPktgen(Prober):
    PARAMETERS = {
        "device": "-i",
        "duration": "-y",
        "frame_size": "-z",
        "src_ip": "-s",
        "src_mac": "-a",
        "dst_ip": "-d",
        "dst_mac": "-m",
        "rate_bps": "-r",
        "rate_pps": "-p",
        "threads": "-t",
        "pkt_clones": "-c",
        "burst": "-b",
    }

    METRICS = {
        "bandwidth": "Estimated throughput",
    }

    def __init__(self):
        Prober.__init__(
            self,
            id=PROBER_PKTGEN,
            name="pktgen",
            parameters=ProberPktgen.PARAMETERS,
            metrics=ProberPktgen.METRICS,
        )
        self._path = "./pktgen/pktgen_cmd.sh"
        self._command = self.load_cmd()

    def load_cmd(self):
        _filepath = os.path.normpath(
            os.path.join(os.path.dirname(__file__), self._path)
        )
        return _filepath

    def options(self, options):
        opts = []
        timeout = None

        for k, v in options.items():
            if k == "-y":
                timeout = float(v)
            opts.extend([k, v])

        settings = {"opts": opts, "timeout": timeout}
        return settings

    def parser(self, results):
        metrics, error = [], ""

        out = results.get("out", [])
        err = results.get("err", "")

        if err:
            error = err

        if out:
            try:
                metrics = json.loads(out)
            except ValueError:
                logger.debug("pktgen json output could not be decoded")

        return metrics, error


if __name__ == "__main__":
    app = ProberPktgen()
    print(app.main())
