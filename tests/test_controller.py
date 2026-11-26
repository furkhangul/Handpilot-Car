"""README §15.1 zorunlu controller senaryoları."""

from handpilot import config
from handpilot.controller import Controller
from handpilot.gesture import GestureResult

DT = 1 / 30


def feed(ctrl, labels, t0=0.0, link_ok=True):
    t = t0
    cmd = None
    for lab in labels:
        cmd = ctrl.update(GestureResult(lab != "yok", lab, 0.99, True, t), link_ok)
        t += DT
    return cmd, t


def driving_ctrl():
    c = Controller()
    cmd, t = feed(c, ["gaz"] * config.FRAMES_GAZ)
    assert cmd.drive
    return c, t


def test_start_needs_five_fists():
    c = Controller()
    cmd, _ = feed(c, ["gaz"] * (config.FRAMES_GAZ - 1))
    assert not cmd.drive
    cmd, _ = feed(c, ["gaz"])
    assert cmd.drive and cmd.turn == "N"


def test_four_fists_and_other_no_start():
    c = Controller()
    cmd, _ = feed(c, ["gaz"] * 4 + ["diger"] + ["gaz"] * 4)
    assert not cmd.drive


def reversing_ctrl():
    c = Controller()
    cmd, t = feed(c, ["geri"] * config.FRAMES_GERI)
    assert cmd.d == -1
    return c, t


def test_two_palms_reverse_from_stop():
    c = Controller()
    cmd, t = feed(c, ["geri"] * (config.FRAMES_GERI - 1))
    assert not cmd.drive
    cmd, _ = feed(c, ["geri"], t)
    assert cmd.d == -1 and cmd.speed == config.SPEED_REVERSE and cmd.mode == "GERI" and cmd.reason == "palm_reverse"


def test_palm_while_forward_switches_to_reverse():
    c, t = driving_ctrl()
    cmd, t = feed(c, ["geri"] * (config.FRAMES_GERI - 1), t)
    assert cmd.d == 1
    cmd, _ = feed(c, ["geri"], t)
    assert cmd.d == -1 and cmd.speed == config.SPEED_REVERSE


def test_fist_while_reversing_switches_to_forward():
    c, t = reversing_ctrl()
    cmd, t = feed(c, ["gaz"] * (config.FRAMES_GAZ - 1), t)
    assert cmd.d == -1
    cmd, _ = feed(c, ["gaz"], t)
    assert cmd.d == 1 and cmd.speed == config.SPEED_NORMAL


def test_reverse_latched_and_steers():
    c, t = reversing_ctrl()
    cmd, t = feed(c, ["sol"] * config.FRAMES_TURN, t)  # Avucu bırakınca da geri devam eder
    assert cmd.d == -1 and cmd.turn == "L"
    cmd, t = feed(c, ["sag"] * config.FRAMES_TURN, t)
    assert cmd.d == -1 and cmd.turn == "R"
    cmd, _ = feed(c, ["geri"] * config.FRAMES_TURN, t)
    assert cmd.d == -1 and cmd.turn == "N"


def test_reverse_stops_when_hand_lost():
    c, t = reversing_ctrl()
    cmd = c.update(GestureResult(False, "yok", 0, False, t - DT + 0.51))
    assert not cmd.drive and cmd.reason == "hand_lost"


def test_turn_while_stopped_does_nothing():
    c = Controller()
    cmd, _ = feed(c, ["sol"] * 20)
    assert not cmd.drive


def test_turn_while_driving_and_back_to_straight():
    c, t = driving_ctrl()
    cmd, t = feed(c, ["sol"] * config.FRAMES_TURN, t)
    assert cmd.turn == "L"
    cmd, t = feed(c, ["sag"] * config.FRAMES_TURN, t)
    assert cmd.turn == "R"
    cmd, _ = feed(c, ["gaz"] * config.FRAMES_TURN, t)
    assert cmd.drive and cmd.turn == "N"


def test_hand_lost_timing():
    c, t = driving_ctrl()
    last_seen = t - DT
    cmd = c.update(GestureResult(False, "yok", 0, False, last_seen + 0.49))
    assert cmd.drive
    cmd = c.update(GestureResult(False, "yok", 0, False, last_seen + 0.51))
    assert not cmd.drive and cmd.reason == "hand_lost"


def test_unknown_one_second_stops():
    c, t = driving_ctrl()
    cmd = c.update(GestureResult(True, "diger", 0.3, False, t))
    cmd = c.update(GestureResult(True, "diger", 0.3, False, t + 0.9))
    assert cmd.drive
    cmd = c.update(GestureResult(True, "diger", 0.3, False, t + 1.0))
    assert not cmd.drive and cmd.reason == "unknown_timeout"


def test_latch_released_after_stop():
    c, t = driving_ctrl()
    cmd = c.update(GestureResult(False, "yok", 0, False, t + 0.6))
    assert not cmd.drive
    t += 0.6
    cmd, t = feed(c, ["diger"] * 10, t)  # Belirsiz hareket aracı kaldırmaz
    assert not cmd.drive
    cmd, _ = feed(c, ["gaz"] * config.FRAMES_GAZ, t)
    assert cmd.drive


def test_gas_latched_without_holding_fist():
    c, t = driving_ctrl()
    cmd, _ = feed(c, ["gaz", "sol", "sol", "sol", "sol"], t)
    assert cmd.drive


def test_link_lost_stops_and_blocks_start():
    c, t = driving_ctrl()
    cmd, t = feed(c, ["gaz"], t, link_ok=False)
    assert not cmd.drive and cmd.reason == "link_lost"
    cmd, _ = feed(c, ["gaz"] * 10, t, link_ok=False)
    assert not cmd.drive


# ---------- Yerinde dönüş (PIVOT_WHEN_STOPPED açıksa) ----------

def test_pivot_when_stopped_while_held(monkeypatch):
    monkeypatch.setattr(config, "PIVOT_WHEN_STOPPED", True)
    c = Controller()
    cmd, t = feed(c, ["sol"] * config.FRAMES_PIVOT)
    assert cmd.mode == "YERINDE" and cmd.turn == "L" and cmd.d == 0
    cmd, t = feed(c, ["sol"] * 20, t)
    assert cmd.mode == "YERINDE"
    cmd, _ = feed(c, ["sag"] * config.HELD_RELEASE_FRAMES, t)   # Bırakınca dur, ters yöne kendiliğinden geçmez
    assert not cmd.drive


def test_gas_after_pivot_needs_full_confirmation(monkeypatch):
    monkeypatch.setattr(config, "PIVOT_WHEN_STOPPED", True)
    c = Controller()
    cmd, t = feed(c, ["sag"] * config.FRAMES_PIVOT)
    cmd, t = feed(c, ["gaz"] * config.HELD_RELEASE_FRAMES, t)
    assert not cmd.drive
    cmd, _ = feed(c, ["gaz"] * config.FRAMES_GAZ, t)
    assert cmd.d == 1
