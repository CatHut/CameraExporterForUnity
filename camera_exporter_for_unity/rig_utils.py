#################################################
# 駆動元リグの解析・指定
# 設計: TSK-00001 RIG-00100 〜 RIG-00300
#################################################

import bpy


LOG = "[CEU:rig]"

# Dolly リグ規約上、画角カスタムプロパティを持つポーズボーンの固定名（RIG-00300）
LENS_BONE_NAME = "Camera"

# 画角ドライバーが参照するカスタムプロパティ名
LENS_PROPERTY_KEY = "lens"


def is_export_camera(self, obj):
    """出力対象カメラとして選択可能なオブジェクトを絞り込む（UI-00200）。"""
    return obj.type == 'CAMERA'


def find_driving_armature(camera_object):
    """カメラの親から駆動元リグを検出する（RIG-00200）。

    親が ARMATURE でなければ None を返す。駆動元リグを持たない
    素のカメラにも対応するため、None は正常系として扱う。
    """
    parent = camera_object.parent
    if parent is None or parent.type != 'ARMATURE':
        return None

    return parent


def find_lens_bone(armature_object):
    """駆動元リグから画角カスタムプロパティを持つボーンを探す（RIG-00300）。

    Dolly リグ規約に従い固定名 'Camera' のポーズボーンを探す。
    存在しない場合や lens カスタムプロパティを持たない場合は None を返す。
    """
    if armature_object is None:
        return None

    pose_bone = armature_object.pose.bones.get(LENS_BONE_NAME)
    if pose_bone is None:
        return None

    if LENS_PROPERTY_KEY not in pose_bone:
        return None

    return pose_bone


def has_lens_driver(camera_object):
    """カメラデータの lens がドライバーで駆動されているかを判定する。"""
    data = camera_object.data
    if data.animation_data is None:
        return False

    for fcurve in data.animation_data.drivers:
        if fcurve.data_path == "lens":
            return True

    return False
