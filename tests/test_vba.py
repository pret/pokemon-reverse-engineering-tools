"""
Tests for VBA automation tools
"""

import unittest

import pokemontools.vba.vba as vba

try:
    import pokemontools.vba.vba_autoplayer as autoplayer
except ImportError:
    import pokemontools.vba.autoplayer as autoplayer

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

    cry = vba.crystal()
    runner = autoplayer.SpeedRunner(cry=cry)

    # skip=False means run the skip_intro function instead of just skipping to
    # a saved state.
    runner.skip_intro()

    state = cry.get_state()

    # clean everything up again
    cry.vba.shutdown()

    return state

class VbaTests(unittest.TestCase):
    # unittest in jython2.5 doesn't seem to have setUpClass ?? Man, why am I on
    # jython2.5? This is ancient.
    #@classmethod
    #def setUpClass(cls):
    #    # get a good game state
    #    cls.state = bootstrap()
    #
    #    # figure out addresses
    #    cls.wram = setup_wram()

    # FIXME: work around jython2.5 unittest
    state = bootstrap()
    wram = setup_wram()

    def get_wram_value(self, name):
        return vba.get_memory_at(self.wram[name])

    def setUp(self):
        # clean the state
        vba.shutdown()
        vba.load_rom()

        # reset to whatever the bootstrapper created
        vba.set_state(self.state)

    def tearDown(self):
        vba.shutdown()

    def test_movement_changes_player_direction(self):
        player_direction = self.get_wram_value("PlayerDirection")

        vba.crystal.move("u")

        # direction should have changed
        self.assertNotEqual(player_direction, self.get_wram_value("PlayerDirection"))

    def test_movement_changes_y_coord(self):
        first_map_y = self.get_wram_value("MapY")

        vba.crystal.move("u")

        # y location should be different
        second_map_y = self.get_wram_value("MapY")
        self.assertNotEqual(first_map_y, second_map_y)

    def test_movement_ends_in_standing(self):
        # should start with standing
        self.assertEqual(self.get_wram_value("PlayerAction"), 1)

        vba.crystal.move("l")

        # should be standing
        player_action = self.get_wram_value("PlayerAction")
        self.assertEqual(player_action, 1) # 1 = standing

class TestEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cry = crystal()

        # advance it forward past the intro sequences
        cls.cry.vba.step(count=3500)

    def test_PlaceString(self):
        self.cry.call(0, 0x1078)

        # where to draw the text
        self.cry.registers["hl"] = 0xc4a0

        # what text to read from
        self.cry.registers["de"] = 0x1276

        self.cry.vba.step(count=10)

        text = self.cry.get_text()

        self.assertTrue("TRAINER" in text)

    def test_keyboard_planner(self):
        button_sequence = keyboard.plan_typing("an")
        expected_result = ["select", "a", "d", "r", "r", "r", "r", "a"]

        self.assertEqual(len(expected_result), len(button_sequence))
        self.assertEqual(expected_result, button_sequence)

if __name__ == "__main__":
    unittest.main()
