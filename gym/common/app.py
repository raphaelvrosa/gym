import logging
import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server

from gym.common.logs import Logs
from gym.common.cfg import Config

logger = logging.getLogger(__name__)


class App:
    def __init__(self, app_cls, app_role):
        self.cfg = Config()
        self.app_cls = app_cls
        self.app_role = app_role

    def logs(self):
        info = self.cfg.get()
        filename = "".join([
            "/tmp/",
            self.__class__.__name__,
            "-",
            info.get("uuid"),
            ".log"])

        Logs(filename, debug=info.get("debug"))

    async def main(self):
        app_args = self.cfg.get()
        address = app_args.get("address")
        host, port = address.split(":")
        logger.debug(f"App serving on host {host} - port {port}")

        if self.app_cls and self.app_role:
            app_args["role"] = self.app_role

            server = Server([self.app_cls(app_args)])
            with graceful_exit([server]):
                await server.start(host, port)
                await server.wait_closed()

        else:
            logger.info(f"Neither app_cls or app_role were defined"
                        f"{self.app_cls} and/or {self.app_role}")

    def init(self):
        self.logs()

        try:
            asyncio.run(self.main())
        except Exception as excpt:
            logger.info(f"Could not init app - exception: {excpt}")
        finally:
            logger.info("App shutdown complete")

    def run(self, argv):
        ack = self.cfg.parse(argv)

        if ack:
            self.init()
        else:
            print(f'App {self.__class__.__name__} finished')
            return -1
