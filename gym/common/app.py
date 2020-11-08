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

    async def main(self):
        """Uses grpclibs to create an async grpc service
        for App, then run the App_cls [Player, Manager, Agent, Monitor, Infra]
        with passed params (app_args)
        Starts server on specified address:port and wait to be closed
        by grpclibs graceful_exit
        OBS: Adds App role to app_args (so Core and Status classes make proper init)
        """
        app_args = self.cfg.get()
        address = app_args.get("address")
        host, port = address.split(":")
        logger.debug(f"App serving on host:port {host}:{port}")

        if self.app_cls and self.app_role:
            app_args["role"] = self.app_role

            server = Server([self.app_cls(app_args)])
            with graceful_exit([server]):
                await server.start(host, port)
                await server.wait_closed()

        else:
            logger.info(
                f"Neither app_cls or app_role were defined"
                f"{self.app_cls} and/or {self.app_role}"
            )

    def logs(self, screen=True):
        """Start logs for application in INFO or DEBUG mode
        Debug allways goes to /tmb/Gym[role][uuid].log file
        Info will be printed on screen
        If --debug set when started, debug will be printed on screen
        """
        info = self.cfg.get()
        filename = "".join(
            ["/tmp/gym/logs/", self.__class__.__name__, "-", info.get("uuid"), ".log"]
        )

        Logs(filename, debug=info.get("debug"), screen=screen)

    def init(self):
        """Starts logs and calls main handling possible exceptions"""
        self.logs()

        try:
            asyncio.run(self.main())
        except Exception as excpt:
            logger.info(f"Could not init app - exception: {excpt}")
        finally:
            logger.info("App shutdown complete")

    def run(self, argv):
        """Parses args (sys.argv) provided when running the App
        And run the App via init() that calls main()
        Only inits if provided args are correct (uuid and address provided)

        Arguments:
            argv {list} -- Arguments passed to App when starting
            command line script (e.g., gym-agent, gym-player, etc)
        """
        ack = self.cfg.parse(argv)

        if ack:
            self.init()
        else:
            print(f"App {self.__class__.__name__} finished")
