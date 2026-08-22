#################################################
# FBX 出力
# 設計: TSK-00001 FBX-00100 〜 FBX-00270 / TSK-00005 FBX-00600
#################################################

import os

import bpy


LOG = "[CEU:fbx]"


def sanitize_filename(name):
    """ファイル名に使えない文字を置換する。"""
    invalid = '<>:"/\\|?*'
    result = name

    for char in invalid:
        result = result.replace(char, "_")

    return result.strip() or "untitled"


def export_fbx(filepath, camera_object, frame_start, frame_end):
    """FBX を出力する（FBX-00100）。

    画角（Focal Length, mm）は camera_object.data が保持する driver 経由で
    Blender の FBX エクスポータが Camera.FocalLength チャンネルとして直接
    出力する（BAKE-00500 / FBX-00600）。scale への値埋め込みは行わない。

    bake_anim_use_all_actions=False の場合、Blender の FBX エクスポータは
    シーンのフレーム範囲を基準にベイクし直す。対象 Action の frame_range と
    シーン範囲がずれているとベイク結果が欠落するため、出力直前にシーンの
    フレーム範囲を frame_start / frame_end に一時的に合わせる（FBX-00260）。
    """
    directory = os.path.dirname(filepath)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    bpy.context.view_layer.objects.active = camera_object

    bpy.ops.object.select_all(action='DESELECT')
    camera_object.select_set(True)

    scene = bpy.context.scene
    original_start = scene.frame_start
    original_end = scene.frame_end

    scene.frame_start = frame_start
    scene.frame_end = frame_end

    try:
        _export_fbx_with_current_frame_range(filepath, camera_object)
    finally:
        scene.frame_start = original_start
        scene.frame_end = original_end

    print(f"{LOG} 出力完了: {filepath}")


def _export_fbx_with_current_frame_range(filepath, camera_object):
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types={'CAMERA'},
        bake_anim=True,
        # 出力時点で camera_object にアサインされている Action は 1 本のみ
        # （BAKE-00100）。True にすると Take 名が {オブジェクト名}｜{Action名}
        # になり、Unity 側の AnimationClip 名に Action 名が反映される
        # （FBX-00270）。False だと Take 名が {オブジェクト名}｜Scene に
        # 固定され Action 名が失われるため、この出力単位（1 Action = 1
        # ファイル）でも True を使う
        bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,
        # 既定値 1.0 ではキーが間引かれモーションが変質する
        bake_anim_simplify_factor=0.0,
        bake_anim_step=1.0,
        add_leaf_bones=False,
        path_mode='COPY',
        embed_textures=False,
    )


def build_animation_filepath(directory, action_name):
    """アニメーションのみ出力のファイルパスを組み立てる（UI-00350）。"""
    filename = f"{sanitize_filename(action_name)}.fbx"
    return os.path.join(bpy.path.abspath(directory), filename)
