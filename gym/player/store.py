import os 
import json 
import logging


logger = logging.getLogger(__name__)


class StorageDisk:
    def __init__(self):
        self.filename = None
        self.folder = "./vnfbr/"
        # self.folder = "../../vnfbr/"

    def filepath(self, filename):
        if not os.path.exists(os.path.dirname(self.folder)):
            os.makedirs(os.path.dirname(self.folder))
        # filepath = os.path.join(os.path.dirname(__file__), self.folder, filename)
        filepath = os.path.join(self.folder, filename)
        return filepath

    def load(self, filename):
        filename = self.filepath(filename)
        with open(filename, 'r') as infile:
            data = json.load(infile)
            return data

    def save(self, commit):
        filename = commit.get("filename")
        filepath = self.filepath(filename)
        data = json.loads(commit.get("data"))
        with open(filepath, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
            return True
        return False

    def store(self, vnfbr):
        logger.debug("Disk Store VNF-BR")
        index_id = vnfbr.get_id()
        vnfbr_json = vnfbr.to_json()
        commit = {'filename': 'vnfbr-' + str(index_id), 'data': vnfbr_json}
        
        if self.save(commit):
            logger.info('ok: vnfbr %s stored', index_id)
        else:
            logger.info('error: vnfbr NOT %s stored', index_id)


class Storage:
    MODES = {
        "disk": StorageDisk,
    }
    
    def __init__(self, defaults=['disk']):
        self.modes = []
        self.load_modes(defaults)

    def load_modes(self, modes):
        for mode in modes:
            if mode in Storage.MODES:
                if mode not in self.modes:
                    self.modes.append(Storage.MODES[mode])
        logger.info("Storage modes set %s", self.modes)

    def store(self, vnfbr):
        for storage in self.modes:
            db = storage()
            db.store(vnfbr)
        return True
