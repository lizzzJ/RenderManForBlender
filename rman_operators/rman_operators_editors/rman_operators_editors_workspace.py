from ...rman_ui.rman_ui_base import CollectionPanel   
from ...rfb_utils.draw_utils import _draw_ui_from_rman_config
from ...rfb_utils import string_utils
from ...rfb_logger import rfb_log
from ...rman_constants import RFB_MAX_USER_TOKENS
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
import bpy

class RENDER_OT_Renderman_Open_Workspace(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_workspace"
    bl_label = "RenderMan Workspace"

    def execute(self, context):
        self.set_tokens(context)
        return{'FINISHED'}         

    def cancel(self, context):
        self.set_tokens(context)

    def set_tokens(self, context):
        string_utils.update_blender_tokens_cb(context.scene)

    def draw_item(self, layout, context, item):
        layout.prop(item, 'name')
        layout.prop(item, 'value')

    def add_callback(self, context):
        rm = context.scene.renderman
        if len(rm.user_tokens) < RFB_MAX_USER_TOKENS:
            return True
        return False

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        layout = self.layout
        rd = context.scene.render
        rm = context.scene.renderman
        is_rman_interactive_running = rm.is_rman_interactive_running

        split = layout.split(factor=0.33)
        col = layout.column()
        col.enabled = not is_rman_interactive_running

        _draw_ui_from_rman_config('rman_properties_scene', 'RENDER_PT_renderman_workspace', context, layout, rm) 

        layout.label(text='Scene Tokens')
        col = layout.column()
        row = col.row()
        row.prop(rm, 'version_token')
        row = col.row()
        row.prop(rm, 'take_token')

        self._draw_collection(context, layout, rm, "User Tokens",
                              "collection.add_remove",
                              "scene.renderman",
                              "user_tokens", "user_tokens_index", 
                              default_name='name_%d' % len(rm.user_tokens),
                              enable_add_func=self.add_callback)        


    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_workspace('INVOKE_DEFAULT')
            
    def __init__(self):
        self.event = None         

    def invoke(self, context, event):

        wm = context.window_manager
        width = rfb_config['editor_preferences']['workspace_editor']['width']
        self.event = event
        return wm.invoke_props_dialog(self, width=width)                      

classes = [
    RENDER_OT_Renderman_Open_Workspace,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():

    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass                                    