


class Plugin:
    
    def start(self, scenario):
        raise NotImplementedError

    def stop(self, scenario=None):
        raise NotImplementedError
    
    def update(self, scenario):
        raise NotImplementedError