bl_info = {
    "name": "NH_BoneCleaner",
    "author": "Nylonheart",
    "version": (1, 4),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Nylonheart",
    "description": "Detect and clean unused bones and vertex groups",
    "category": "Rigging",
}

import bpy
from bpy.props import PointerProperty, StringProperty, EnumProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup
from collections import Counter

def get_vertex_group_weights(obj, group_name):
    idx = obj.vertex_groups.find(group_name)
    if idx == -1:
        return []
    weights = []
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == idx:
                weights.append(g.weight)
    return weights

def find_common_armature_modifier(meshes):
    mod_name_counts = Counter()
    mod_map = {}
    for mesh in meshes:
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                mod_name_counts[mod.name] += 1
                mod_map[mod.name] = mod.object
    common = [name for name, count in mod_name_counts.items() if count == len(meshes)]
    return [(name, name, "") for name in common], mod_map

class BoneCleanerProperties(PropertyGroup):
    modifier_name: EnumProperty(
        name="Modifier",
        items=lambda self, context: find_common_armature_modifier([obj for obj in context.selected_objects if obj.type == 'MESH'])[0]
    )
    preserve_hierarchy: BoolProperty(
        name="Preserve Bone Hierarchy",
        description="Keep parent bones of used bones, even if they are unused themselves",
        default=True
    )

class BONECLEANER_OT_SelectUnusedBones(Operator):
    bl_idname = "bonecleaner.select_unused_bones"
    bl_label = "Select Unused Bones"
    bl_description = "Select bones not used by the selected mesh objects"

    def execute(self, context):
        props = context.scene.bone_cleaner_props
        mod_name = props.modifier_name
        preserve_hierarchy = props.preserve_hierarchy

        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'ERROR'}, "At least one mesh must be selected.")
            return {'CANCELLED'}

        common_mods, mod_map = find_common_armature_modifier(meshes)
        arm = mod_map.get(mod_name)
        if not arm:
            self.report({'ERROR'}, "Modifier not found or inconsistent across meshes.")
            return {'CANCELLED'}

        used_bones = set()
        for mesh in meshes:
            mod = mesh.modifiers.get(mod_name)
            if not mod or mod.type != 'ARMATURE' or mod.object != arm:
                continue
            for vg in mesh.vertex_groups:
                weights = get_vertex_group_weights(mesh, vg.name)
                if any(w > 0.0 for w in weights):
                    used_bones.add(vg.name)

        if preserve_hierarchy:
            expanded_set = set()
            for bone_name in used_bones:
                bone = arm.data.bones.get(bone_name)
                while bone:
                    expanded_set.add(bone.name)
                    bone = bone.parent
            used_bones = expanded_set

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')

        for bone in arm.data.edit_bones:
            bone.select = bone.name not in used_bones

        return {'FINISHED'}

class BONECLEANER_OT_DeleteSelectedBones(Operator):
    bl_idname = "bonecleaner.delete_selected_bones"
    bl_label = "Delete Selected Bones"
    bl_description = "Delete currently selected bones in Edit Mode"

    def execute(self, context):
        if context.mode != 'EDIT_ARMATURE':
            self.report({'ERROR'}, "Must be in Edit Mode for Armature.")
            return {'CANCELLED'}

        bpy.ops.armature.delete()
        return {'FINISHED'}

class BONECLEANER_OT_DeleteUnusedVertexGroups(Operator):
    bl_idname = "bonecleaner.delete_unused_vertex_groups"
    bl_label = "Delete Unused Vertex Groups"
    bl_description = "Delete vertex groups with no weights"

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not meshes:
            self.report({'ERROR'}, "At least one mesh must be selected.")
            return {'CANCELLED'}

        total_removed = 0
        for mesh in meshes:
            used = set()
            for v in mesh.data.vertices:
                for g in v.groups:
                    if g.weight > 0:
                        used.add(g.group)

            to_remove = [vg.name for i, vg in enumerate(mesh.vertex_groups) if i not in used]
            for name in to_remove:
                mesh.vertex_groups.remove(mesh.vertex_groups[name])
            total_removed += len(to_remove)

        self.report({'INFO'}, f"Removed {total_removed} vertex groups.")
        return {'FINISHED'}

class BONECLEANER_PT_Panel(Panel):
    bl_label = "Rig Bone Cleaner"
    bl_idname = "BONECLEANER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nylonheart'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bone_cleaner_props

        selected_meshes = [obj.name for obj in context.selected_objects if obj.type == 'MESH']
        if selected_meshes:
            layout.label(text="Selected Meshes:")
            for name in selected_meshes:
                layout.label(text=name, icon='MESH_DATA')
            layout.prop(props, "modifier_name")
        else:
            layout.label(text="Select one or more mesh objects.", icon='ERROR')

        layout.prop(props, "preserve_hierarchy")

        layout.operator("bonecleaner.select_unused_bones", icon='BONE_DATA')
        layout.operator("bonecleaner.delete_selected_bones", icon='TRASH')
        layout.separator()
        layout.operator("bonecleaner.delete_unused_vertex_groups", icon='GROUP_VERTEX')

def register():
    bpy.utils.register_class(BoneCleanerProperties)
    bpy.types.Scene.bone_cleaner_props = PointerProperty(type=BoneCleanerProperties)

    for cls in [
        BONECLEANER_OT_SelectUnusedBones,
        BONECLEANER_OT_DeleteSelectedBones,
        BONECLEANER_OT_DeleteUnusedVertexGroups,
        BONECLEANER_PT_Panel,
    ]:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Scene.bone_cleaner_props

    for cls in reversed([
        BONECLEANER_OT_SelectUnusedBones,
        BONECLEANER_OT_DeleteSelectedBones,
        BONECLEANER_OT_DeleteUnusedVertexGroups,
        BONECLEANER_PT_Panel,
        BoneCleanerProperties,
    ]):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
