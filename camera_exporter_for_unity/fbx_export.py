#################################################
# FBX 出力
# 設計: TSK-00001 FBX-00100 〜 FBX-00250
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


def export_fbx(filepath, camera_object):
    """FBX を出力する（FBX-00100）。

    画角（Focal Length, mm）は出力用カメラの scale.x に埋め込まれている
    （FBX-00250）。Blender の FBX エクスポータは Transform チャンネルの
    F カーブのみを書き出すため、この方式でアニメーションが渡る。

    bake_anim_use_all_actions=True のため、camera_object が保持する全
    Action がそれぞれ AnimStack として書き出される（FBX-00410）。各
    Action は自身の frame_range に基づいてベイクされるため、シーンの
    フレーム範囲を操作する必要はない（FBX-00420）。
    """
    directory = os.path.dirname(filepath)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    bpy.context.view_layer.objects.active = camera_object

    bpy.ops.object.select_all(action='DESELECT')
    camera_object.select_set(True)

    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types={'CAMERA'},
        bake_anim=True,
        # 対象オブジェクトが保持する全 Action を AnimStack として出力する
        # （FBX-00410）。Take 名は {オブジェクト名}｜{Action名} になる
        bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,
        # 既定値 1.0 ではキーが間引かれモーションが変質する
        bake_anim_simplify_factor=0.0,
        bake_anim_step=1.0,
        add_leaf_bones=False,
        path_mode='COPY',
        embed_textures=False,
    )

    print(f"{LOG} 出力完了: {filepath}")


def build_export_filepath(directory, camera_name):
    """出力ファイルパスを組み立てる（FBX-00400）。"""
    filename = f"{sanitize_filename(camera_name)}.fbx"
    return os.path.join(bpy.path.abspath(directory), filename)
