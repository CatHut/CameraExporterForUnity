#################################################
# Action の選択と管理
# 設計: TSK-00001 ACT-00100 〜 ACT-00300
#################################################

import bpy


LOG = "[CEU:action]"


def find_action_slot(action, target_object):
    """Action 内から target_object に割り当て可能なスロットを探す。

    Blender 4.4+ の slotted action に対応する（ACT-00200）。
    見つからなければ None を返す。
    """
    if not hasattr(action, "slots"):
        return None

    for slot in action.slots:
        id_type = getattr(slot, "target_id_type", None)
        if id_type is None or id_type == 'OBJECT':
            return slot

    return None


def is_action_bakeable(action, target_object):
    """Action が target_object に対してベイク可能かを判定する（UI-00250）。"""
    if action is None or target_object is None:
        return False

    if find_action_slot(action, target_object) is None:
        return False

    if len(action.fcurves) == 0:
        return False

    return True


def collect_bakeable_actions(target_object):
    """target_object に対してベイク可能な Action を列挙する。"""
    if target_object is None:
        return []

    return [a for a in bpy.data.actions if is_action_bakeable(a, target_object)]


def get_action_frame_range(action):
    """Action のフレーム範囲を int で返す（BAKE-00200）。"""
    start, end = action.frame_range
    return int(round(start)), int(round(end))


def store_animation_state(target_object):
    """Action のアサイン状態を退避する（ACT-00300 / SAFE-00100）。"""
    ad = target_object.animation_data
    if ad is None:
        return {"had_animation_data": False, "action": None, "slot": None}

    slot = None
    try:
        slot = ad.action_slot
    except AttributeError:
        pass

    return {
        "had_animation_data": True,
        "action": ad.action,
        "slot": slot,
    }


def restore_animation_state(target_object, state):
    """store_animation_state() で退避した状態を復元する。"""
    if state is None:
        return

    ad = target_object.animation_data

    if not state["had_animation_data"]:
        if ad is not None:
            target_object.animation_data_clear()
        return

    if ad is None:
        ad = target_object.animation_data_create()

    ad.action = state["action"]

    if state["slot"] is not None:
        try:
            ad.action_slot = state["slot"]
        except (AttributeError, TypeError) as e:
            print(f"{LOG} スロット復元に失敗: {e}")


def assign_action(target_object, action):
    """Action とスロットを target_object にアサインする（ACT-00200）。

    成功した場合 True を返す。
    """
    ad = target_object.animation_data
    if ad is None:
        ad = target_object.animation_data_create()

    ad.action = action

    slot = find_action_slot(action, target_object)
    if slot is None:
        print(f"{LOG} '{action.name}' に割り当て可能なスロットがありません")
        return False

    try:
        ad.action_slot = slot
    except (AttributeError, TypeError) as e:
        print(f"{LOG} '{action.name}' のスロット割り当てに失敗: {e}")
        return False

    return True
