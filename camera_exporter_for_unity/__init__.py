#################################################
# CameraExporterForUnity
#
# Blender の Dolly カメラリグが駆動するカメラのトランスフォームと
# 画角アニメーションを、Unity 向け FBX として出力するアドオン。
#
# 設計: .claude/Task/active/TSK-00001-camera-exporter.md
#################################################

bl_info = {
    "name": "CameraExporterForUnity",
    "author": "CatHut",
    "version": (0, 1, 0),
    # スロット付き Action（Blender 4.4+）に依存する
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Camera",
    "description": "Export Dolly camera rig animations to Unity-ready FBX",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

from . import rig_utils
from . import action_utils
from . import bake_utils
from . import fbx_export
from . import exporter
from . import properties
from . import ui


def register():
    properties.register()
    ui.register()


def unregister():
    ui.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
