import os
import yaml

class Config:

    def __init__(self):
        self.path = os.getcwd()
        stream = open(self.path + "/project_config.yaml", 'r')

        data = yaml.load(stream)
        opts = data.keys()

        for k in opts:
            setattr(self, k, data.get(k))
            

config = Config()