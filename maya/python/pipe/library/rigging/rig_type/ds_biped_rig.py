from pipe.library.rigging.ds_rig import Rig
from pipe.library.utilities.validate import ds_validate
from pipe.library.rigging.rig_type.builders.ds_biped_limb_builder import BipedLimbBuilder

### Biped Rig class inheriting from the base Rig class.
class Biped_Rig(Rig):
    def __init__(self, rig_name):
        super().__init__(rig_name)
        print(f"Biped Rig initialized with name: {rig_name}")

    ## Method to create limb rigs for biped characters. #This will go to LimbBuilder
    def limb_biped(self, name, start_joint, end_joint, sc_joint = None):
        ds_validate.validate_limb_inputs(start_joint, end_joint, sc_joint)
        BipedLimbBuilder(self.rig_name, start_joint, end_joint, sc_joint).build()

    def spine_biped(self, start_joint, end_joint):
        print(f"Creating spine rig... from {start_joint} to {end_joint} name: {self.rig_name}")


    def foot_biped(self, foot_joint):
        print(f"Creating foot rig... foot joint: {foot_joint} name: {self.rig_name}")