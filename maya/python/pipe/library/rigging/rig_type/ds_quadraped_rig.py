from pipe.library.rigging.ds_rig import Rig

class Quadraped_Rig(Rig):
    def __init__(self, name):
        super().__init__(name)
        print(f"Quadruped Rig initialized with name: {self.rig_name}")