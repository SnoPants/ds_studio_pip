from pipe.library.rigging.ds_rig import Rig

class Face_Rig(Rig):
    def __init__(self, name):
        super().__init__(name)
        print(f"Face Rig initialized with name: {self.rig_name}")