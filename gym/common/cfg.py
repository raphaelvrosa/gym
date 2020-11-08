import logging
import argparse


logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self._info = None
        self.parser = argparse.ArgumentParser(description="Gym App")

    def get(self):
        return self._info

    def check_address_fmt(self, address):
        ack = True

        try:
            ip, port = address.split(":")
        except ValueError as e:
            print(f"Address must contain ip:port format")
            print(f"Exception checking address format {e}")
            ack = False
        else:
            if not ip or not port:
                print(f"Address must contain ip and port")
                ack = False

        finally:
            return ack

    def check_contact_fmt(self, contacts):
        acks = []
        roles = ["agent", "monitor", "manager", "player", "infra"]

        for contact in contacts:
            ack = True

            try:
                role, address = contact.split("/")
                ack = self.check_address_fmt(address)

            except ValueError as e:
                print(f"Contact {contact} must contain role/ip:port format")
                print(f"Exception checking contact {e}")

            finally:
                if role in roles and ack:
                    acks.append(True)
                else:
                    print(f"Check if contact {contact} role in {roles}")
                    acks.append(False)

        if all(acks):
            return True
        else:
            print(f"Not all contacts in correct format (e.g., role/ip:port)")
            return False

    def check_cfg(self):
        """Checks if config parameters were passed in correct format
        i.e., check if address is in host:port valid formats
        i.e., check if contacts contain role/host:port format

        Returns:
            bool -- If config parameters are correct or not
        """
        address_ok = self.check_address_fmt(self.cfg.address)

        contacts_ok = True
        if self.cfg.contacts:
            contacts_ok = self.check_contact_fmt(self.cfg.contacts)

        ack = address_ok and contacts_ok
        return ack

    def get_cfg_attrib(self, name):
        try:
            value = getattr(self.cfg, name)
        except AttributeError as e:
            logger.debug(f"Argparser attrib name not found - exception {e}")
            value = None
        finally:
            return value

    def check(self):
        _contacts = None

        _id, _address = self.cfg.uuid, self.cfg.address
        _contacts = self.cfg.contacts

        if _id and _address:
            if self.check_cfg():
                info = {
                    "uuid": _id,
                    "address": _address,
                    "contacts": _contacts,
                    "debug": self.cfg.debug,
                }
                print(f"App cfg args OK: id {_id} - address {_address}")
                return info

            else:
                return None
        else:
            print(
                f"App cfg args not provided - both must exist:"
                f"uuid and address (provided values: {_id} and {_address})"
            )
            return None

    def parse(self, argv=None):
        """Parses all the initial configuration parameters of any gym app
        Checks if mandatory app parameters (uuid and address) were provided correctly

        Keyword Arguments:
            argv {list} -- List of arguments initially passed by the App (default: {None})

        Returns:
            bool -- If all the mandatory parameters (uuid and address) were in argv
        """

        print(f"Initializing Gym App - Parsing Argv")

        self.parser.add_argument(
            "--uuid", type=str, help="Define the app unique id (default: None)"
        )

        self.parser.add_argument(
            "--address",
            type=str,
            help="Define the app address (host:port) (default: None)",
        )

        self.parser.add_argument(
            "--contacts",
            nargs="+",
            help="Define the app contacts - role/address "
            "(e.g., agent/localhost:18080) (default: [])",
        )

        self.parser.add_argument(
            "--debug",
            action="store_true",
            help="Define the app logging mode (default: False)",
        )

        self.cfg, _ = self.parser.parse_known_args(argv)
        info = self.check()

        if info:
            self._info = info
            return True

        return False
