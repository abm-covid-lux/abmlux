
import yaml

def load_config(filename):
    with open(filename) as fin:
        return yaml.load(fin, Loader=yaml.FullLoader)
