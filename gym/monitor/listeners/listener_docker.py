import logging

logger = logging.getLogger(__name__)

import docker

from gym.monitor.listeners.listener import Listener
from gym.common.defs import LISTENER_DOCKER

import time
from datetime import datetime

# Based on: https://github.com/signalfx/docker-collectd-plugin/blob/master/dockerplugin.py


class ListenerDocker(Listener):
    PARAMETERS = {
        "interval": "interval",
        "target": "target",
        "duration": "duration",
    }

    METRICS = {
        0: "system_cpu_usage",
        1: "cpu_total_usage",
        2: "cpu_usage_in_kernelmode",
        3: "cpu_usage_in_usermode",
        4: "cpu_percent",
        5: "mem_active_anon",
        6: "mem_active_file",
        7: "mem_cache",
        8: "mem_dirty",
        9: "mem_hierarchical_memory_limit",
        10: "mem_hierarchical_memsw_limit",
        11: "mem_inactive_anon",
        12: "mem_inactive_file",
        13: "mem_mapped_file",
        14: "mem_pgfault",
        15: "mem_pgmajfault",
        16: "mem_pgpgin",
        17: "mem_pgpgout",
        18: "mem_rss",
        19: "mem_rss_huge",
        20: "mem_total_active_anon",
        21: "mem_total_active_file",
        22: "mem_total_cache",
        23: "mem_total_dirty",
        24: "mem_total_inactive_anon",
        25: "mem_total_inactive_file",
        26: "mem_total_mapped_file",
        27: "mem_total_pgfault",
        28: "mem_total_pgmajfault",
        29: "mem_total_pgpgin",
        30: "mem_total_pgpgout",
        31: "mem_total_rss",
        32: "mem_total_rss_huge",
        33: "mem_total_unevictable",
        34: "mem_total_writeback",
        35: "mem_unevictable",
        36: "mem_writeback",
        37: "mem_percent",
        38: "mem_limit",
        39: "mem_max_usage",
        40: "mem_usage",
        41: "io_read",
        42: "io_write",
    }

    def __init__(self, url=None):
        Listener.__init__(
            self,
            id=LISTENER_DOCKER,
            name="docker",
            parameters=ListenerDocker.PARAMETERS,
            metrics=ListenerDocker.METRICS,
        )
        self._command = None
        self._connected_to_docker = False
        self._url = url
        if not url:
            self._url = "unix://var/run/docker.sock"
        self.connect()

    def connect(self):
        try:
            self._dc = docker.from_env()
            # self._dc = docker.DockerClient(base_url=self.url)
        except Exception as e:
            self._dc = None
            logger.warn(
                "could not connect to docker socket - check if docker is installed/running %s",
                e,
            )
        else:
            self._connected_to_docker = True

    def _stats_cpu(self, stats):
        summary_stats_cpu = {}
        cpu_stats = stats["cpu_stats"]
        cpu_usage = cpu_stats["cpu_usage"]
        # summary_stats_cpu['cpu_throttling_data'] = cpu_stats['throttling_data']
        summary_stats_cpu["system_cpu_usage"] = cpu_stats["system_cpu_usage"]
        summary_stats_cpu["cpu_total_usage"] = cpu_usage["total_usage"]
        summary_stats_cpu["cpu_usage_in_kernelmode"] = cpu_usage["usage_in_kernelmode"]
        summary_stats_cpu["cpu_usage_in_usermode"] = cpu_usage["usage_in_usermode"]
        # summary_stats_cpu['percpu_usage'] = cpu_usage['percpu_usage']
        summary_stats_cpu["cpu_percent"] = self._stats_cpu_perc(stats)
        # print(self._get_docker_cpu(stats))
        return summary_stats_cpu

    def _stats_cpu_perc(self, stats):
        cpu_stats = stats["cpu_stats"]
        cpu_usage = cpu_stats["cpu_usage"]
        system_cpu_usage = cpu_stats["system_cpu_usage"]
        # percpu = cpu_usage['percpu_usage']
        cpu_percent = 0.0

        if "online_cpus" in stats["cpu_stats"]:
            online_cpus = stats["cpu_stats"]["online_cpus"]
        else:
            online_cpus = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"] or [])

        if "precpu_stats" in stats:
            precpu_stats = stats["precpu_stats"]
            precpu_usage = precpu_stats["cpu_usage"]
            cpu_delta = cpu_usage["total_usage"] - precpu_usage["total_usage"]
            system_delta = system_cpu_usage - precpu_stats["system_cpu_usage"]
            if system_delta > 0 and cpu_delta > 0:
                # cpu_percent = (100.0 * (cpu_delta / system_delta)) * len(percpu)
                cpu_percent = (100.0 * (cpu_delta / system_delta)) * online_cpus
        return cpu_percent

    def _stats_mem(self, stats):
        summary_stats_mem = {}
        mem_stats = stats["memory_stats"]

        in_mem_stats = mem_stats["stats"]
        for k, v in in_mem_stats.items():
            new_k = "mem_" + k
            summary_stats_mem[new_k] = v

        summary_stats_mem["mem_percent"] = self._stats_mem_perc(stats)
        summary_stats_mem["mem_limit"] = mem_stats["limit"]
        summary_stats_mem["mem_max_usage"] = mem_stats["max_usage"]
        summary_stats_mem["mem_usage"] = mem_stats["usage"]
        return summary_stats_mem

    def _stats_mem_perc(self, stats):
        mem_stats = stats["memory_stats"]
        mem_percent = 100.0 * mem_stats["usage"] / mem_stats["limit"]
        return mem_percent

    def _stats_blkio(self, stats):
        blkio_values = {}
        blkio_stats = stats["blkio_stats"]

        blkio_values["io_read"] = 0
        blkio_values["io_write"] = 0
        for key, values in blkio_stats.items():
            # Block IO stats are reported by block device (with major/minor
            # numbers). We need to group and report the stats of each block
            # device independently.
            if key == "io_service_bytes_recursive":
                for value in values:
                    # k = '{key}-{major}-{minor}'.format(key=key,
                    #                                    major=value['major'],
                    #                                    minor=value['minor'])
                    # if k not in device_stats:
                    #     device_stats[k] = {}
                    # device_stats[k][value['op']] = value['value']
                    if value["op"] == "Read":
                        if value["value"] >= blkio_values["io_read"]:
                            blkio_values["io_read"] = value["value"]
                    if value["op"] == "Write":
                        if value["value"] >= blkio_values["io_write"]:
                            blkio_values["io_write"] = value["value"]

            # for type_instance, values in device_stats.items():
            #     if len(values) == 5:
            #         blkio_values[type_instance] = values
            #     elif len(values) == 1:
            #         blkio_values[key] = values
            # For some reason, some fields contains only one value and
            # the 'op' field is empty. Need to investigate this
            # else:
            #     pass
        return blkio_values

    def _stats(self, name=None):
        summary_stats = {}

        container = self._dc.containers.get(name)
        if container:
            stats = container.stats(stream=False)
        else:
            return summary_stats

        stats_cpu = self._stats_cpu(stats)
        summary_stats.update(stats_cpu)
        stats_mem = self._stats_mem(stats)
        summary_stats.update(stats_mem)
        stats_io = self._stats_blkio(stats)
        summary_stats.update(stats_io)
        return summary_stats

    def options(self, options):
        timeout = None
        args = {}

        for k, v in options.items():
            # if k == "stop":
            #     stop = True
            if k == "duration":
                timeout = v
            args[k] = v

        settings = {"opts": opts, "timeout": timeout}
        return settings

    def monitor(self, opts):
        results = []
        interval = 1
        t = 3

        if "interval" in opts:
            interval = float(opts["interval"])
        if "duration" in opts:
            t = float(opts["duration"])

        if "target" in opts:
            name = opts["target"]
        else:
            return results

        past = datetime.now()
        while True:
            current = datetime.now()
            seconds = (current - past).total_seconds()
            if seconds > t:
                break
            else:
                measurement = self._stats(name=name)
                if "read" in measurement:
                    del measurement["read"]

                results.append(measurement)
                time.sleep(interval)

        results = {
            "code": 0,
            "out": results,
            "err": "",
        }
        return results

    def parser(self, results):
        metrics, error = [], ""

        out = results.get("out", [])
        err = results.get("err", "")

        if err:
            error = err

        if out:
            metric_names = list(out[0].keys())

            for name in metric_names:

                metric_values = dict(
                    [
                        (
                            out.index(out_value),
                            {
                                "key": out.index(out_value),
                                "value": float(out_value.get(name)),
                            },
                        )
                        for out_value in out
                    ]
                )

                m = {
                    "name": name,
                    "type": "float",
                    "unit": "",
                    "series": metric_values,
                }

                metrics.append(m)

        return metrics, error


if __name__ == "__main__":
    opts = {
        # "interval": "1",
        "duration": "3",
        "target": "hammurabi",
    }

    # docker_listener = ListenerDocker()
    # measures = docker_listener.monitor(opts)
    # metrics = docker_listener.parser(measures)
    # for v in metrics:
    #     print(v)

    app = ListenerDocker()
    print(app.main())
