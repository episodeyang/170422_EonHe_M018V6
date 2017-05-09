__author__ = 'Ge Yang'
import yaml

class EonHeExperiment():
    def __init__(self, config_file_path=None):
        with open(config_file_path, 'r') as config_file:
            # save text of yaml config in datacache
            # self.config_text = config_file.readlines()
            self.config = yaml.load(config_file)

    def configure(self, config=None):
        if not config:
            config = self.config
        else:
            # Note: not sure if overwriting is the right thing to do.
            self.config = config

    def make_data_dir(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)

    def init_filament(self, filament_parameters):
        self.fil = filament.settup_driver()



if __name__ == "__main__":
    eonhe = EonHeExperiment('./eonhe-test.yml')