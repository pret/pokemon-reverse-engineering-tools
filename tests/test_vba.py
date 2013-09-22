"""
Tests for VBA automation tools
"""

import unittest

import pokemontools.vba.vba as vba

try:
    import pokemontools.vba.vba_autoplayer as autoplayer
except ImportError:
    import pokemontools.vba.autoplayer as autoplayer

import pokemontools.vba.keyboard as keyboard

autoplayer.vba = vba

def setup_wram():
    """
    Loads up some default addresses. Should eventually be replaced with the
    actual wram parser.
    """
    wram = {}
    wram["PlayerDirection"] = 0xd4de
    wram["PlayerAction"] = 0xd4e1
    wram["MapX"] = 0xd4e6
    wram["MapY"] = 0xd4e7
    return wram

def bootstrap():
    """
    Every test needs to be run against a certain minimum context. That context
    is constructed by this function.
    """

    cry = vba.crystal(config=None)
    runner = autoplayer.SpeedRunner(cry=cry)

    # skip=False means run the skip_intro function instead of just skipping to
    # a saved state.
    runner.skip_intro(skip=True)

    state = cry.vba.state

    # clean everything up again
    cry.vba.shutdown()

    return state

class OtherVbaTests(unittest.TestCase):
    def test_keyboard_planner(self):
        button_sequence = keyboard.plan_typing("an")
        expected_result = ["select", "a", "d", "r", "r", "r", "r", "a"]

        self.assertEqual(len(expected_result), len(button_sequence))
        self.assertEqual(expected_result, button_sequence)

class VbaTests(unittest.TestCase):
    cry = None
    wram = None

    @classmethod
    def setUpClass(cls):
        cls.bootstrap_state = bootstrap()

        cls.wram = setup_wram()

        cls.cry = vba.crystal()
        cls.vba = cls.cry.vba

        cls.vba.state = cls.bootstrap_state

    @classmethod
    def tearDownClass(cls):
        cls.vba.shutdown()

    def setUp(self):
        # reset to whatever the bootstrapper created
        self.vba.state = self.bootstrap_state

    def get_wram_value(self, name):
        return self.vba.memory[self.wram[name]]

    def test_movement_changes_player_direction(self):
        player_direction = self.get_wram_value("PlayerDirection")

        self.cry.move("u")

        # direction should have changed
        self.assertNotEqual(player_direction, self.get_wram_value("PlayerDirection"))

    def test_movement_changes_y_coord(self):
        first_map_y = self.get_wram_value("MapY")

        self.cry.move("u")

        # y location should be different
        second_map_y = self.get_wram_value("MapY")
        self.assertNotEqual(first_map_y, second_map_y)

    def test_movement_ends_in_standing(self):
        # should start with standing
        self.assertEqual(self.get_wram_value("PlayerAction"), 1)

        self.cry.move("l")

        # should be standing
        player_action = self.get_wram_value("PlayerAction")
        self.assertEqual(player_action, 1) # 1 = standing

    def test_PlaceString(self):
        self.cry.call(0, 0x1078)

        # where to draw the text
        self.cry.registers["hl"] = 0xc4a0

        # what text to read from
        self.cry.registers["de"] = 0x1276

        self.cry.vba.step(count=10)

        text = self.cry.get_text()

        self.assertTrue("TRAINER" in text)

if __name__ == "__main__":
    unittest.main()
