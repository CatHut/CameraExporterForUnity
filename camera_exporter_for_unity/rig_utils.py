#################################################
# 駆動元リグの解析・指定
# 設計: TSK-00001 RIG-00100 〜 RIG-00200
#################################################

import bpy


LOG = "[CEU:rig]"


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

