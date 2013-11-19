"""
Tests for VBA automation tools
"""

import unittest

from setup_vba import (
    vba,
    autoplayer,
    keyboard,
)

from bootstrapping import (
    bootstrap,
    bootstrap_trainer_battle,
)

def setup_wram():
    """
    Loads up some default addresses. Should eventually be replaced with the
    actual wram parser.
    """
    # TODO: this should just be parsed straight out of wram.asm
    wram = {}
    wram["PlayerDirection"] = 0xd4de
    wram["PlayerAction"] = 0xd4e1
    wram["MapX"] = 0xd4e6
    wram["MapY"] = 0xd4e7

    wram["WarpNumber"] = 0xdcb4
    wram["MapGroup"] = 0xdcb5
    wram["MapNumber"] = 0xdcb6
    wram["YCoord"] = 0xdcb7
    wram["XCoord"] = 0xdcb8

    return wram

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

    def check_movement(self, direction="d"):
        """
        Check if (y, x) before attempting to move and (y, x) after attempting
        to move are the same.
        """
        start = (self.get_wram_value("MapY"), self.get_wram_value("MapX"))
        self.cry.move(direction)
        end = (self.get_wram_value("MapY"), self.get_wram_value("MapX"))
        return start != end

    def bootstrap_name_prompt(self):
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(stop_at_name_selection=True, skip=False, override=False)

        self.cry.vba.press("a", hold=20)

        # wait for "Your name?" to show up
        while "YOUR NAME?" not in self.cry.get_text():
            self.cry.step(count=50)

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

    def test_speedrunner_constructor(self):
        runner = autoplayer.SpeedRunner(cry=self.cry)

    def test_speedrunner_handle_mom(self):
        # TODO: why can't i pass in the current state of the emulator?
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(skip=True)
        runner.handle_mom(skip=False)

        # confirm that handle_mom is done by attempting to move on the map
        self.assertTrue(self.check_movement("d"))

    def test_speedrunner_walk_into_new_bark_town(self):
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(skip=True)
        runner.handle_mom(skip=True)
        runner.walk_into_new_bark_town(skip=False)

        # test that the game is in a state such that the player can walk
        self.assertTrue(self.check_movement("d"))

        # check that the map is correct
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 4)

    def test_speedrunner_handle_elm(self):
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(skip=True)
        runner.handle_mom(skip=True)
        runner.walk_into_new_bark_town(skip=False)

        # go through the Elm's Lab sequence
        runner.handle_elm("cyndaquil", skip=False)

        # test again if the game is in a state where the player can walk
        self.assertTrue(self.check_movement("u"))

        # check that the map is correct
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 5)

    def test_moving_back_and_forth(self):
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(skip=True)
        runner.handle_mom(skip=True)
        runner.walk_into_new_bark_town(skip=False)

        # must be in New Bark Town
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 4)

        runner.cry.move("l")
        runner.cry.move("l")
        runner.cry.move("l")
        runner.cry.move("d")
        runner.cry.move("d")

        for x in range(0, 10):
            runner.cry.move("l")
            runner.cry.move("d")
            runner.cry.move("r")
            runner.cry.move("u")

        # must still be in New Bark Town
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 4)

    def test_crystal_move_list(self):
        runner = autoplayer.SpeedRunner(cry=None)
        runner.setup()
        runner.skip_intro(skip=True)
        runner.handle_mom(skip=True)
        runner.walk_into_new_bark_town(skip=False)

        # must be in New Bark Town
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 4)

        first_map_x = self.get_wram_value("MapX")

        runner.cry.move(["l", "l", "l"])

        # x location should be different
        second_map_x = self.get_wram_value("MapX")
        self.assertNotEqual(first_map_x, second_map_x)

        # must still be in New Bark Town
        self.assertEqual(self.get_wram_value("MapGroup"), 24)
        self.assertEqual(self.get_wram_value("MapNumber"), 4)

    def test_keyboard_typing_dumb_name(self):
        self.bootstrap_name_prompt()

        name = "tRaInEr"
        self.cry.write(name)

        # save this selection
        self.cry.vba.press("a", hold=20)

        self.assertEqual(name, self.cry.get_player_name())

    def test_keyboard_typing_cap_name(self):
        names = [
            "trainer",
            "TRAINER",
            "TrAiNeR",
            "tRaInEr",
            "ExAmPlE",
            "Chris",
            "Kris",
            "beepaaa",
            "chris",
            "CHRIS",
            "Python",
            "pYthon",
            "pyThon",
            "pytHon",
            "pythOn",
            "pythoN",
            "python",
            "PyThOn",
            "Zot",
            "Death",
            "Hiro",
            "HIRO",
        ]

        self.bootstrap_name_prompt()
        start_state = self.cry.vba.state

        for name in names:
            print "Writing name: " + name

            self.cry.vba.state = start_state

            sequence = self.cry.write(name)

            print "sequence is: " + str(sequence)

            # save this selection
            self.cry.vba.press("start", hold=20)
            self.cry.vba.press("a", hold=20)

            pname = self.cry.get_player_name().replace("@", "")
            self.assertEqual(name, pname)

if __name__ == "__main__":
    unittest.main()
