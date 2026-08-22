#################################################
# エクスポート処理の本体
# 設計: TSK-00001 BAKE-00100 / SAFE-00100 〜 SAFE-00300
#################################################

import bpy

from . import action_utils
from . import bake_utils
from . import fbx_export
from . import rig_utils


LOG = "[CEU:export]"


class ExportContext:
    """エクスポート中に生成した一時データを追跡する（SAFE-00300）。"""

    def __init__(self):
        self.objects = []
        self.actions = []

    def add_object(self, obj):
        self.objects.append(obj)

    def add_action(self, action):
        self.actions.append(action)

    def cleanup(self):
        """一時データを全て破棄する。"""
        for obj in self.objects:
            if obj is None:
                continue

            data = obj.data

            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except (ReferenceError, RuntimeError) as e:
                print(f"{LOG} オブジェクト削除に失敗: {e}")
                continue

            if data is None or data.users > 0:
                continue

            try:
                bpy.data.cameras.remove(data)
            except (ReferenceError, RuntimeError) as e:
                print(f"{LOG} データブロック削除に失敗: {e}")

        for action in self.actions:
            if action is None:
                continue

            try:
                action.use_fake_user = False
                bpy.data.actions.remove(action)
            except (ReferenceError, RuntimeError) as e:
                print(f"{LOG} Action 削除に失敗: {e}")

        self.objects.clear()
        self.actions.clear()


def store_selection_state(context):
    """選択状態とモードを退避する（SAFE-00100）。"""
    active = context.view_layer.objects.active

    return {
        "active": active,
        "selected": [obj for obj in context.view_layer.objects if obj.select_get()],
        "frame": context.scene.frame_current,
    }


def restore_selection_state(context, state):
    """store_selection_state() で退避した状態を復元する。"""
    context.scene.frame_set(state["frame"])

    active = state["active"]
    try:
        if active is not None:
            context.view_layer.objects.active = active
    except ReferenceError:
        pass

    try:
        bpy.ops.object.select_all(action='DESELECT')
    except RuntimeError as e:
        print(f"{LOG} 選択解除に失敗: {e}")

    for obj in state["selected"]:
        try:
            obj.select_set(True)
        except ReferenceError:
            pass


def build_export_camera(source_camera):
    """出力用カメラオブジェクトを複製する（BAKE-00100 手順 1-2）。

    親子関係は解除し、ワールド空間のトランスフォームをそのまま持たせる。
    """
    export_data = source_camera.data.copy()
    export_camera = source_camera.copy()
    export_camera.data = export_data
    export_camera.name = f"{bake_utils.BAKED_ACTION_PREFIX}{source_camera.name}"

    matrix_world = source_camera.matrix_world.copy()
    export_camera.parent = None
    export_camera.matrix_world = matrix_world

    bpy.context.collection.objects.link(export_camera)

    return export_camera


def run_export(context, report):
    """エクスポート処理の全体フロー（BAKE-00100）。

    戻り値: (成功したか, 出力したファイルパスのリスト)
    """
    scene = context.scene
    settings = scene.ceu_settings

    source_camera = settings.source_camera
    if source_camera is None:
        report({'ERROR'}, "カメラが選択されていません")
        return False, []

    driving_armature = rig_utils.find_driving_armature(source_camera)
    assign_target = driving_armature if driving_armature is not None else source_camera

    actions = action_utils.collect_bakeable_actions(assign_target)
    if not actions:
        report({'ERROR'}, "ベイク可能な Action がありません")
        return False, []

    export_ctx = ExportContext()

    selection_state = store_selection_state(context)
    animation_state = action_utils.store_animation_state(assign_target)

    try:
        if context.view_layer.objects.active is not None:
            if context.view_layer.objects.active.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

        export_camera = build_export_camera(source_camera)
        export_ctx.add_object(export_camera)

        bake_utils.add_copy_transforms(export_camera, source_camera)

        for action in actions:
            baked = bake_utils.bake_action(
                context, export_camera, source_camera, driving_armature, action)

            if baked is None:
                continue

            export_ctx.add_action(baked)

        bake_utils.remove_copy_transforms(export_camera)

        filepath = fbx_export.build_export_filepath(
            settings.export_directory, source_camera.name)
        fbx_export.export_fbx(filepath, export_camera)

        return True, [filepath]

    finally:
        export_ctx.cleanup()

        action_utils.restore_animation_state(assign_target, animation_state)
        restore_selection_state(context, selection_state)

        print(f"{LOG} 後始末完了")
