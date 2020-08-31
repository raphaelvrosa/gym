import logging
import time
from gym.common.defs import PROBER_IPERF
from gym.agent.probers.prober import Prober

logger = logging.getLogger()


class ProberIperf(Prober):
    PARAMETERS = {
        "port": "-p",
        "duration": "-t",
        "protocol": "-u",
        "server": "-s",
        "client": "-c",
    }

    METRICS = {
        "bandwidth": "Estimated throughput",
    }

    def __init__(self):
        Prober.__init__(
            self,
            id=PROBER_IPERF,
            name="iperf",
            parameters=ProberIperf.PARAMETERS,
            metrics=ProberIperf.METRICS,
        )
        self._command = "iperf"

    def options(self, options):
        opts = []
        timeout = None
        if "-c" in options:
            time.sleep(0.5)  # FIX

        for k, v in options.items():
            # if k == "-s":
            #     stop = True
            if k == "-t":
                timeout = float(v)
            if k == "-u" or k == "-s":
                opts.extend([k])
            else:
                opts.extend([k, v])
        opts.extend(["-f", "m"])

        settings = {"opts": opts, "timeout": timeout}
        return settings

    def parser(self, results):
        metrics, error = [], ""

        out = results.get("out", [])
        err = results.get("err", "")

        if err:
            error = err

        if out:
            lines = [line for line in out.split("\n") if line.strip()]

            if len(lines) == 7:
                bandwidth = lines[-1].split(" ")[-2]
                units = lines[-1].split(" ")[-1]
                m = {
                    "name": "throughput",
                    "series": False,
                    "type": "float",
                    "unit": units,
                    "value": float(bandwidth),
                }
                metrics = [m]

            elif len(lines) == 11 or len(lines) == 8:
                bandwidth = lines[-1].split(" ")[-13]
                units = lines[-1].split(" ")[-12]

                m = {
                    "name": "throughput",
                    "series": False,
                    "type": "float",
                    "unit": units,
                    "value": float(bandwidth),
                }
                metrics = [m]

        return metrics, error


if __name__ == "__main__":
    app = ProberIperf()
    print(app.main())
