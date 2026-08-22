#################################################
# オペレータと UI パネル
# 設計: TSK-00001 UI-00100 〜 UI-00450
#################################################

import bpy
from bpy.types import Operator, Panel, UIList

from . import action_utils
from . import exporter
from . import properties
from . import rig_utils


LOG = "[CEU:ui]"


#################################################
# オペレータ
#################################################

class CEU_OT_RefreshActions(Operator):
    """Action リストを再構築する"""
    bl_idname = "ceu.refresh_actions"
    bl_label = "Refresh Action List"
    bl_options = {'REGISTER'}

    def execute(self, context):
        properties.refresh_action_list(context.scene)
        return {'FINISHED'}


class CEU_OT_Export(Operator):
    """対象カメラの全 Action を Unity 向け FBX として出力する"""
    bl_idname = "ceu.export"
    bl_label = "Export FBX"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.ceu_settings

        if settings.source_camera is None:
            return False

        driving_armature = rig_utils.find_driving_armature(settings.source_camera)
        assign_target = driving_armature if driving_armature is not None else settings.source_camera

        return len(action_utils.collect_bakeable_actions(assign_target)) > 0

    def execute(self, context):
        try:
            success, exported = exporter.run_export(context, self.report)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.report({'ERROR'}, f"エクスポートに失敗しました: {e}")
            return {'CANCELLED'}

        if not success:
            return {'CANCELLED'}

        if not exported:
            self.report({'WARNING'}, "出力されたファイルがありません")
            return {'CANCELLED'}

        self.report({'INFO'}, f"{len(exported)} 個の FBX を出力しました")
        return {'FINISHED'}


#################################################
# Action リスト
#################################################

class CEU_UL_ActionList(UIList):
    """ベイク対象 Action の一覧（参照専用、UI-00500）"""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.name, icon='CAMERA_DATA')

            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text=f"{item.frame_start} - {item.frame_end}")

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.name)


#################################################
# UI パネル
#################################################

class CEU_PT_ExportPanel(Panel):
    """エクスポート設定パネル（UI-00100 / UI-00400）"""

    bl_label = "CameraExporter"
    bl_idname = "CEU_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Camera'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.ceu_settings

        # 出力対象カメラの選択（UI-00200）
        box = layout.box()
        box.label(text="Camera:")
        box.prop(settings, "source_camera", text="")

        if settings.source_camera is None:
            box.label(text="カメラを選択してください", icon='ERROR')
            return

        # ベイク対象 Action の一覧表示（参照専用、UI-00500）
        box = layout.box()
        header = box.row(align=True)
        header.label(text="Actions:")
        header.operator("ceu.refresh_actions", text="", icon='FILE_REFRESH')

        box.template_list(
            "CEU_UL_ActionList", "",
            settings, "action_items",
            settings, "action_index",
            rows=4,
        )

        if len(settings.action_items) == 0:
            box.label(text="ベイク可能な Action がありません", icon='INFO')
        else:
            box.label(text=f"{len(settings.action_items)} 件を出力します")

        # 出力設定
        box = layout.box()
        box.label(text="Output:")
        box.prop(settings, "export_directory", text="")

        # 実行
        layout.separator()
        layout.operator("ceu.export", icon='EXPORT')


classes = (
    CEU_OT_RefreshActions,
    CEU_OT_Export,
    CEU_UL_ActionList,
    CEU_PT_ExportPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
