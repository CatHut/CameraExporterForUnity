#################################################
# プロパティ定義
# 設計: TSK-00001 UI-00200 / UI-00250 / UI-00450
#################################################

import bpy
from bpy.props import (
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from . import action_utils
from . import rig_utils


LOG = "[CEU:props]"


class CEU_ActionItem(PropertyGroup):
    """ベイク対象 Action の 1 行（参照専用、UI-00500）。"""

    name: StringProperty(name="Action Name")

    frame_start: IntProperty(name="Start")
    frame_end: IntProperty(name="End")


def get_action_assign_target(camera_object):
    """Action の選択リスト構築に使う対象を返す（駆動元リグ、なければカメラ自身）。"""
    if camera_object is None:
        return None

    driving_armature = rig_utils.find_driving_armature(camera_object)
    return driving_armature if driving_armature is not None else camera_object


def refresh_action_list(scene):
    """Action リストを再構築する（参照専用、UI-00500）。"""
    settings = scene.ceu_settings

    settings.action_items.clear()

    target = get_action_assign_target(settings.source_camera)
    if target is None:
        return

    for action in action_utils.collect_bakeable_actions(target):
        item = settings.action_items.add()
        item.name = action.name

        start, end = action_utils.get_action_frame_range(action)
        item.frame_start = start
        item.frame_end = end

    print(f"{LOG} Action リストを再構築: {len(settings.action_items)} 件")


def on_source_camera_changed(self, context):
    """出力対象カメラが変更されたら Action リストを作り直す。"""
    refresh_action_list(context.scene)


class CEU_Settings(PropertyGroup):
    """アドオンの設定一式。Scene に保存する（UI-00450）。"""

    source_camera: PointerProperty(
        name="Camera",
        description="出力対象のカメラ",
        type=bpy.types.Object,
        poll=rig_utils.is_export_camera,
        update=on_source_camera_changed,
    )

    action_items: CollectionProperty(type=CEU_ActionItem)

    action_index: IntProperty(default=0)

    export_directory: StringProperty(
        name="Output Directory",
        description="FBX の出力先ディレクトリ",
        subtype='DIR_PATH',
        default="//",
    )


classes = (
    CEU_ActionItem,
    CEU_Settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ceu_settings = PointerProperty(type=CEU_Settings)


def unregister():
    del bpy.types.Scene.ceu_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
