from library.rigging.ds_rig import Rig

class Mechanical_Rig(Rig):
    def __init__(self, name):
        super().__init__(name)
        print(f"Mechanical Rig initialized with name: {self.rig_name}")