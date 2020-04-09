import logging
import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server

from gym.common.logs import Logs
from gym.common.cfg import Config

logger = logging.getLogger(__name__)


class App:
    def __init__(self):
        self.cfg = Config()

    def logs(self):
        prefix = self.__class__.__name__
        info = self.cfg.get()
        filename = "/tmp/" + prefix + str(info.get("uuid")) + ".log"
        Logs(filename, debug=info.get("debug"))

    async def main(self, app_cls, app_args):
        address = app_args.get("address")
        server = Server([app_cls(app_args)])

        host, port = address.split(":")
        logger.debug(f"Starting server on host {host} : port {port}")

        with graceful_exit([server]):
            await server.start(host, port)
            print(f"Serving on {host}:{port}")
            await server.wait_closed()

    def init(self, app_cls):
        self.logs()
        app_args = self.cfg.get()

        try:
            asyncio.run(self.main(app_cls, app_args))
        except Exception as excpt:
            logger.info(f"Could not init app - exception: {excpt}")

        finally:
            logger.info("App shutdown complete")

    async def shutdown(self):
        logger.info("Cleaning up")
        loop = asyncio.get_event_loop()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
        loop.close()
