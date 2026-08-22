#################################################
# オペレータと UI パネル
# 設計: TSK-00001 UI-00100 〜 UI-00450
#################################################

import bpy
from bpy.types import Operator, Panel, UIList

from . import exporter
from . import properties


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


class CEU_OT_SelectAllActions(Operator):
    """Action の選択状態を一括で切り替える"""
    bl_idname = "ceu.select_all_actions"
    bl_label = "Select All Actions"
    bl_options = {'REGISTER', 'UNDO'}

    select: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in context.scene.ceu_settings.action_items:
            item.selected = self.select

        return {'FINISHED'}


class CEU_OT_Export(Operator):
    """選択した Action を Unity 向け FBX として出力する"""
    bl_idname = "ceu.export"
    bl_label = "Export FBX"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.ceu_settings

        if settings.source_camera is None:
            return False

        return any(item.selected for item in settings.action_items)

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
    """エクスポート対象 Action の一覧（UI-00250）"""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name, icon='CAMERA_DATA')

            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text=f"{item.frame_start} - {item.frame_end}")

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(item, "selected", text="")


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

        # Action の選択（UI-00250）
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

        row = box.row(align=True)
        row.operator("ceu.select_all_actions", text="All").select = True
        row.operator("ceu.select_all_actions", text="None").select = False

        selected_count = sum(1 for item in settings.action_items if item.selected)
        box.label(text=f"選択中: {selected_count} 件")

        # 出力設定
        box = layout.box()
        box.label(text="Output:")
        box.prop(settings, "export_directory", text="")

        # 実行
        layout.separator()
        layout.operator("ceu.export", icon='EXPORT')


classes = (
    CEU_OT_RefreshActions,
    CEU_OT_SelectAllActions,
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
