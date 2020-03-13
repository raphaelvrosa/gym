import logging
import argparse
import yaml

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self._info = None

    def get(self):
        return self._info

    def load(self, filename):
        data = {}
        with open(filename, 'r') as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        return data

    def parse(self, argv=None):
        parser = argparse.ArgumentParser(
            description='Gym App')

        parser.add_argument('--uuid',
                            type=str,
                            help='Define the app unique id (default: None)')

        parser.add_argument('--address',
                            type=str,
                            help='Define the app address (host:port) (default: None)')

        parser.add_argument('--contacts',
                            nargs='+',
                            help='Define the app contacts - role/address (e.g., agent/localhost:18080) (default: [])')

        parser.add_argument('--debug',
                            action='store_true',
                            help='Define the app logging mode (default: False)')

        parser.add_argument('--cfg',
                            type=str,
                            help='Define the yaml cfg file (id + address) (default: None)')

        self.cfg, _ = parser.parse_known_args(argv)
        
        info = self.check()
        if info:
            self._info = info
            return True
        
        return False

    def cfg_args(self):
        cfgFile = self.cfg.cfg
        if cfgFile:
            cfg_data = self.load(cfgFile)
            return cfg_data
        return None
            
    def check(self):
        _contacts = None

        if self.cfg.cfg:
            cfg_data = self.cfg_args()
            _id = cfg_data.get('uuid', None)
            _address = cfg_data.get('address', None)
            _contacts = cfg_data.get('contacts', None)
        else:
            _id, _address = self.cfg.uuid, self.cfg.address
            _contacts = self.cfg.contacts

        if _id and _address:
            logger.info("Init cfg: id %s - address %s", _id, _address)
            info = {
                "uuid": _id,
                "address": _address,
                "contacts": _contacts,
                "debug": self.cfg.debug
            }
            print(f'Argv: {info}')
            return info
        else:
            print("Init cfg NOT provided - both must exist: id and address (provided values: %s, %s)" % (_id, _address))
            return None
