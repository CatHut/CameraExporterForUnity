#################################################
# ベイク処理
# 設計: TSK-00001 BAKE-00100 〜 BAKE-00200 / TSK-00005 BAKE-00500 〜 BAKE-00520
#################################################

import bpy

from . import action_utils


LOG = "[CEU:bake]"

BAKED_ACTION_PREFIX = "CEU_"

# 複製カメラに張るコンストレイントの名前
COPY_TRANSFORMS_NAME = "CEU_CopyTransforms"


def add_copy_transforms(export_camera, source_camera):
    """複製カメラに元カメラへの Copy Transforms コンストレイントを張る
    （BAKE-00100 手順 3）。

    画角（lens, mm）は export_camera が保持する driver（複製元カメラから
    そのままコピーされたもの）経由で FBX エクスポータが直接出力するため
    （BAKE-00500）、scale をコンストレイントの上書き対象から除外する
    必要はない（BAKE-00510）。
    """
    constraint = export_camera.constraints.new('COPY_TRANSFORMS')
    constraint.name = COPY_TRANSFORMS_NAME
    constraint.target = source_camera

    return constraint


def remove_copy_transforms(export_camera):
    """add_copy_transforms() で張ったコンストレイントを削除する（BAKE-00100 手順 5）。"""
    constraint = export_camera.constraints.get(COPY_TRANSFORMS_NAME)
    if constraint is not None:
        export_camera.constraints.remove(constraint)


def bake_transform(context, export_camera, action, actions_before):
    """カメラのトランスフォームをベイクする（BAKE-00100 手順 4-ii）。

    export_camera 自身に対して nla.bake() を実行する。複製カメラは
    Copy Transforms 経由で元カメラ（駆動元リグ）を参照しているため、
    ベイクすることでワールド空間のトランスフォームが焼き付く。

    画角（lens）は export_camera.data が保持する driver 経由で FBX
    エクスポータが直接出力するため（BAKE-00500）、ここでは扱わない。

    actions_before は呼び出し前の bpy.data.actions スナップショット。
    ベイクの副産物 Action を正しく破棄するため、呼び出し側から受け取る。

    戻り値: 生成された Action（失敗時は None）
    """
    frame_start, frame_end = action_utils.get_action_frame_range(action)
    print(f"{LOG} トランスフォームをベイク: {frame_start} - {frame_end}")

    context.view_layer.update()
    context.view_layer.objects.active = export_camera

    bpy.ops.object.select_all(action='DESELECT')
    export_camera.select_set(True)

    bpy.ops.nla.bake(
        frame_start=frame_start,
        frame_end=frame_end,
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        clear_parents=False,
        use_current_action=False,
        bake_types={'OBJECT'},
    )

    baked = export_camera.animation_data.action
    if baked is None:
        print(f"{LOG} トランスフォームのベイク結果を取得できませんでした")
        return None

    for leftover in set(bpy.data.actions) - actions_before:
        if leftover is baked:
            continue

        try:
            leftover.use_fake_user = False
            bpy.data.actions.remove(leftover)
        except (ReferenceError, RuntimeError) as e:
            print(f"{LOG} 副産物 Action の破棄に失敗: {e}")

    return baked


def bake_action(context, export_camera, source_camera, driving_armature, action):
    """1 本の Action をベイクする（BAKE-00100 手順 4）。

    Action とスロットのアサイン先は駆動元リグ（存在する場合）、
    なければカメラ自身とする。

    戻り値: 生成されたベイク済み Action（失敗時は None）
    """
    assign_target = driving_armature if driving_armature is not None else source_camera

    if not action_utils.assign_action(assign_target, action):
        print(f"{LOG} '{action.name}' のアサインに失敗。スキップします")
        return None

    actions_before = set(bpy.data.actions)

    baked = bake_transform(context, export_camera, action, actions_before)
    if baked is None:
        return None

    baked.name = f"{BAKED_ACTION_PREFIX}{action.name}"
    baked.use_fake_user = True

    return baked
