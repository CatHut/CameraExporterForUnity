#################################################
# ベイク処理
# 設計: TSK-00001 BAKE-00100 〜 BAKE-00300
#################################################

import bpy

from . import action_utils
from . import rig_utils


LOG = "[CEU:bake]"

BAKED_ACTION_PREFIX = "CEU_"

# 複製カメラに張るコンストレイントの名前
COPY_LOCATION_NAME = "CEU_CopyLocation"
COPY_ROTATION_NAME = "CEU_CopyRotation"


def add_copy_transforms(export_camera, source_camera):
    """複製カメラに元カメラへの位置・回転コピーを張る（BAKE-00100 手順 3）。

    Copy Transforms（scale を含む）ではなく Copy Location + Copy Rotation を
    使う。scale.x には画角（lens, mm）を埋め込むため（BAKE-00300）、
    scale がコンストレイントで上書きされないようにする必要がある。
    """
    loc_constraint = export_camera.constraints.new('COPY_LOCATION')
    loc_constraint.name = COPY_LOCATION_NAME
    loc_constraint.target = source_camera

    rot_constraint = export_camera.constraints.new('COPY_ROTATION')
    rot_constraint.name = COPY_ROTATION_NAME
    rot_constraint.target = source_camera

    return loc_constraint, rot_constraint


def remove_copy_transforms(export_camera):
    """add_copy_transforms() で張ったコンストレイントを削除する（BAKE-00100 手順 5）。"""
    for name in (COPY_LOCATION_NAME, COPY_ROTATION_NAME):
        constraint = export_camera.constraints.get(name)
        if constraint is not None:
            export_camera.constraints.remove(constraint)


def bake_transform(context, export_camera, action, actions_before):
    """カメラのトランスフォーム（画角埋め込みの scale を含む）をベイクする
    （BAKE-00100 手順 4-iii）。

    export_camera 自身に対して nla.bake() を実行する。複製カメラは
    Copy Transforms 経由で元カメラ（駆動元リグ）を参照しているため、
    ベイクすることでワールド空間のトランスフォームが焼き付く。
    scale.x に事前に打った画角キー（BAKE-00300）も同時にベイクされる。

    actions_before は stamp_lens_into_scale_x() 実行前の bpy.data.actions
    スナップショット。画角埋め込みで新規生成される Action も副産物として
    正しく破棄するため、呼び出し側から受け取る。

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


def stamp_lens_into_scale_x(context, export_camera, source_camera, lens_bone, frame_start, frame_end):
    """画角（lens, mm）を scale.x へ埋め込むキーフレームを打つ（BAKE-00300）。

    Blender の FBX エクスポータはボーン・オブジェクトの Transform チャンネル
    以外の F カーブを一切書き出さない（カメラデータの lens プロパティ・
    カスタムプロパティのいずれも実測で確認済み）。カメラの scale は
    レンダリング結果に影響しないため、Transform チャンネル経由で画角を
    渡す手段として scale.x に mm 値をそのまま代入する。

    ここで打ったキーは bake_transform() の nla.bake() でベイクされる
    前段階の下準備であり、この関数単体ではベイクを完了しない。

    lens_bone が None の場合は静的な画角として扱い、scale は (1, 1, 1) の
    まま変更しない（RIG-00300）。
    """
    export_camera.scale.y = 1.0
    export_camera.scale.z = 1.0

    if lens_bone is None:
        export_camera.scale.x = 1.0
        print(f"{LOG} 画角ドライバーなし。scale.x は 1.0 のまま出力")
        return

    print(f"{LOG} 画角を scale.x へ埋め込み: {frame_start} - {frame_end}")

    original_frame = context.scene.frame_current

    try:
        for frame in range(frame_start, frame_end + 1):
            context.scene.frame_set(frame)
            context.view_layer.update()
            export_camera.scale.x = source_camera.data.lens
            export_camera.keyframe_insert(data_path="scale", index=0, frame=frame)
    finally:
        context.scene.frame_set(original_frame)


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

    frame_start, frame_end = action_utils.get_action_frame_range(action)

    # stamp_lens_into_scale_x() が export_camera に新規 Action を生成しうるため、
    # その前の状態を副産物判定の基準にする
    actions_before = set(bpy.data.actions)

    lens_bone = rig_utils.find_lens_bone(driving_armature)
    stamp_lens_into_scale_x(
        context, export_camera, source_camera, lens_bone, frame_start, frame_end)

    baked = bake_transform(context, export_camera, action, actions_before)
    if baked is None:
        return None

    baked.name = f"{BAKED_ACTION_PREFIX}{action.name}"
    baked.use_fake_user = True

    return baked
