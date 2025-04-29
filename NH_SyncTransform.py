bl_info = {
    "name": "NH_SyncTransform",
    "blender": (4, 4, 0),
    "category": "Animation",
    "author": "Nylonheart",
    "version": (1, 1),
    "description": "Sync rotation, location and scale of same-named bones between two Armatures."
}

import bpy

# -----------------------------------------------------------------------------
# Constants & Helpers
# -----------------------------------------------------------------------------

PREFIXES = {
    "ROT": "NH_SYNC_ROT_",
    "LOC": "NH_SYNC_LOC_",
    "SCL": "NH_SYNC_SCL_",
}
ALL_PREFIXES = tuple(PREFIXES.values())


def get_common_bone_names(armature1, armature2):
    """Return sorted list of bone names common to both armatures."""
    return sorted(set(armature1.pose.bones.keys()) & set(armature2.pose.bones.keys()))


def has_sync_constraint(bone):
    """Check if the bone already has any NH sync constraint."""
    return any(c.name.startswith(ALL_PREFIXES) for c in bone.constraints)


def _remove_existing_constraints(bone):
    for c in list(bone.constraints):
        if c.name.startswith(ALL_PREFIXES):
            bone.constraints.remove(c)


def _new_constraint(bone, ctype, name, source, subtarget):
    con = bone.constraints.new(type=ctype)
    con.name = name
    con.target = source
    con.subtarget = subtarget
    con.target_space = "WORLD"
    con.owner_space = "WORLD"
    return con


def apply_constraints(source, target, common_bones):
    """Apply rotation, location, and scale copy constraints for each common bone."""
    for bone_name in common_bones:
        tgt_bone = target.pose.bones.get(bone_name)
        if not tgt_bone:
            continue

        _remove_existing_constraints(tgt_bone)

        # Copy Rotation
        rot = _new_constraint(
            tgt_bone,
            "COPY_ROTATION",
            PREFIXES["ROT"] + bone_name,
            source,
            bone_name,
        )
        rot.use_x = rot.use_y = rot.use_z = True
        rot.mix_mode = "REPLACE"

        # Copy Location
        loc = _new_constraint(
            tgt_bone,
            "COPY_LOCATION",
            PREFIXES["LOC"] + bone_name,
            source,
            bone_name,
        )
        loc.use_x = loc.use_y = loc.use_z = True

        # Copy Scale
        scl = _new_constraint(
            tgt_bone,
            "COPY_SCALE",
            PREFIXES["SCL"] + bone_name,
            source,
            bone_name,
        )
        scl.use_x = scl.use_y = scl.use_z = True


def remove_constraints(target):
    """Remove any NH sync constraints, even if only a subset remain."""
    for bone in target.pose.bones:
        _remove_existing_constraints(bone)

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------


class NH_OT_ApplySyncTransform(bpy.types.Operator):
    bl_idname = "nh.apply_sync_transform"
    bl_label = "Apply Transform Sync"
    bl_description = "Apply copy constraints (rotation, location, scale) to matching bones"

    def execute(self, context):
        scn = context.scene
        source = scn.nh_sync_source
        target = scn.nh_sync_target

        if not source or not target:
            self.report({'WARNING'}, "Source and Target Armature must be set")
            return {'CANCELLED'}

        common_bones = get_common_bone_names(source, target)
        apply_constraints(source, target, common_bones)
        self.report({'INFO'}, f"Applied constraints to {len(common_bones)} bones")
        return {'FINISHED'}


class NH_OT_RemoveSyncTransform(bpy.types.Operator):
    bl_idname = "nh.remove_sync_transform"
    bl_label = "Remove Transform Sync"
    bl_description = "Remove all NH_SYNC_* constraints"

    def execute(self, context):
        target = context.scene.nh_sync_target
        if not target:
            self.report({'WARNING'}, "Target Armature must be set")
            return {'CANCELLED'}

        remove_constraints(target)
        self.report({'INFO'}, "Removed sync constraints")
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# UI Panel
# -----------------------------------------------------------------------------


class NH_PT_SyncTransformPanel(bpy.types.Panel):
    bl_label = "Rig Sync Transform"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nylonheart'

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Source box
        box_source = layout.box()
        box_source.label(text="Source Armature")
        box_source.prop(scn, "nh_sync_source", text="")

        # Target box
        box_target = layout.box()
        box_target.label(text="Target Armature")
        box_target.prop(scn, "nh_sync_target", text="")

        source = scn.nh_sync_source
        target = scn.nh_sync_target

        # Matching bones
        if source and target:
            common = get_common_bone_names(source, target)
            box_match = layout.box()
            box_match.label(text=f"Matching bones: {len(common)}")
            for name in common:
                tgt_bone = target.pose.bones.get(name)
                synced = tgt_bone and has_sync_constraint(tgt_bone)

                row = box_match.row(align=True)
                row.label(icon='CHECKMARK' if synced else 'BLANK1', text="")
                row.label(icon='BONE_DATA', text="")
                row.label(text=name)

        # Buttons
        layout.operator("nh.apply_sync_transform", icon='CON_TRACKTO')
        layout.operator("nh.remove_sync_transform", icon='X')

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------


def register():
    bpy.utils.register_class(NH_OT_ApplySyncTransform)
    bpy.utils.register_class(NH_OT_RemoveSyncTransform)
    bpy.utils.register_class(NH_PT_SyncTransformPanel)

    bpy.types.Scene.nh_sync_source = bpy.props.PointerProperty(
        name="Source Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    bpy.types.Scene.nh_sync_target = bpy.props.PointerProperty(
        name="Target Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )


def unregister():
    bpy.utils.unregister_class(NH_OT_ApplySyncTransform)
    bpy.utils.unregister_class(NH_OT_RemoveSyncTransform)
    bpy.utils.unregister_class(NH_PT_SyncTransformPanel)

    del bpy.types.Scene.nh_sync_source
    del bpy.types.Scene.nh_sync_target


if __name__ == "__main__":
    register()
