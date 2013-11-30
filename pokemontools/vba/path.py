"""
path finding implementation

1) For each position on the map, create a node representing the position.
2) For each NPC/item, mark nearby nodes as members of that NPC's threat zone
   (note that they can be members of multiple zones simultaneously).
"""

import pokemontools.configuration
config = pokemontools.configuration.Config()

import pokemontools.crystal
import pokemontools.map_gfx

from PIL import (
    Image,
    ImageDraw,
)

PENALTIES = {
    # The minimum cost for a step must be greater than zero or else the path
    # finding implementation might take the player through elaborate routes
    # through nowhere.
    "NONE": 1,

    # for any area that might be near a trainer or moving object
    "THREAT_ZONE": 50,

    # for any nodes that might be under active observation (sight) by a trainer
    "SIGHT_RANGE": 80,

    # active sight range is where the trainer will definitely see the player
    "ACTIVE_SIGHT_RANGE": 100,

    # This is impossible, but the pathfinder might have a bug, and it would be
    # nice to know about such a bug very soon.
    "COLLISION": -999999,
}

DIRECTIONS = {
    "UP": "UP",
    "DOWN": "DOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
}

class Node(object):
    """
    A ``Node`` represents a position on the map.
    """

    def __init__(self, position, threat_zones=None, contents=None):
        self.position = position
        self.y = position[0]
        self.x = position[1]

        # by default a node is not a member of any threat zones
        self.threat_zones = threat_zones or set()

        # by default a node does not have any objects at this location
        self.contents = contents or set()

        self.cost = self.calculate_cost()

    def calculate_cost(self, PENALTIES=PENALTIES):
        """
        Calculates a cost associated with passing through this node.
        """
        penalty = PENALTIES["NONE"]

        # 1) assign a penalty based on whether or not this object is passable,
        # if it's a collision then return a priority immediately
        if self.is_collision_by_map_data() or self.is_collision_by_map_obstacle():
            penalty += PENALTIES["COLLISION"]
            return penalty

        # 2) assign a penalty based on whether or not this object is grass/water

        # 3) assign a penalty based on whether or not there is a map_obstacle here,
        # check each of the contents to see if there are any objects that exist
        # at this location, if anything exists here then return a priority immediately

        # 4) consider any additional penalties due to the presence of a threat
        # zone. Only calculate detailed penalties about the threat zone if the
        # player is within range.
        for threat_zone in self.threat_zones:
            # the player might be inside the threat zone or the player might be
            # just on the boundary
            player_y = get_player_y()
            player_x = get_player_x()
            if threat_zone.is_player_near(player_y, player_x):
                consider_sight_range = True
            else:
                consider_sight_range = False

            penalty += threat_zone.calculate_node_cost(self.y, self.x, consider_sight_range=consider_sight_range, PENALTIES=PENALTIES)

        return penalty

    def is_collision_by_map_data(self):
        """
        Checks if the player can walk on this location.
        """
        raise NotImplementedError

    def is_collision_by_map_obstacle(self):
        """
        Checks if there is a map_obstacle on the current position that prevents
        the player walking here.
        """
        for content in self.contents:
            if self.content.y == self.y and self.content.x == self.x:
                return True
        else:
            return False

class MapObstacle(object):
    """
    A ``MapObstacle`` represents an item, npc or trainer on the map.
    """

    def __init__(self, some_map, identifier, sight_range=None, movement=None, turn=None, simulation=False, facing_direction=DIRECTIONS["DOWN"]):
        """
        :param some_map: a reference to the map that this object belongs to
        :param identifier: which object on the map does this correspond to?
        :param simulation: set to False to not read from RAM
        """
        self.simulation = simulation

        self.some_map = some_map
        self.identifier = identifier

        self._sight_range = sight_range
        if self._sight_range is None:
            self._sight_range = self._get_sight_range()

        self._movement = movement
        if self._movement is None:
            self._movement = self._get_movement()

        self._turn = turn
        if self._turn is None:
            self._turn = self._get_turn()

        self.facing_direction = facing_direction
        if not self.facing_direction:
            self.facing_direction = self.get_current_facing_direction()

        self.update_location()

    def update_location(self):
        """
        Determines the (y, x) location of the given map_obstacle object, which
        can be a reference to an item, npc or trainer npc.
        """
        if self.simulation:
            return (self.y, self.x)
        else:
            raise NotImplementedError

            self.y = new_y
            self.x = new_x

            return (new_y, new_x)

    def _get_current_facing_direction(self, DIRECTIONS=DIRECTIONS):
        """
        Get the current facing direction of the map_obstacle.
        """
        raise NotImplementedError

    def get_current_facing_direction(self, DIRECTIONS=DIRECTIONS):
        """
        Get the current facing direction of the map_obstacle.
        """
        if not self.simulation:
            self.facing_direction = self._get_current_facing_direction(DIRECTIONS=DIRECTIONS)
        return self.facing_direction

    def _get_movement(self):
        """
        Figures out the "movement" variable. Also, this converts from the
        internal game's format into True or False for whether or not the object
        is capable of moving.
        """
        raise NotImplementedError

    @property
    def movement(self):
        if self._movement is None:
            self._movement = self._get_movement()
        return self._movement

    def can_move(self):
        """
        Checks if this map_obstacle is capable of movement.
        """
        return self.movement

    def _get_turn(self):
        """
        Checks whether or not the map_obstacle can turn. This only matters for
        trainers.
        """
        raise NotImplementedError

    @property
    def turn(self):
        if self._turn is None:
            self._turn = self._get_turn()
        return self._turn

    def can_turn_without_moving(self):
        """
        Checks whether or not the map_obstacle can turn. This only matters for
        trainers.
        """
        return self.turn

    def _get_sight_range(self):
        """
        Figure out the sight range of this map_obstacle.
        """
        raise NotImplementedError

    @property
    def sight_range(self):
        if self._sight_range is None:
            self._sight_range = self._get_sight_range()
        return self._sight_range

class ThreatZone(object):
    """
    A ``ThreatZone`` represents the area surrounding a moving or turning object
    that the player can try to avoid.
    """

    def __init__(self, map_obstacle, main_graph):
        """
        Constructs a ``ThreatZone`` based on a graph of a map and a particular
        object on that map.

        :param map_obstacle: the subject based on which to build a threat zone
        :param main_graph: a reference to the map's nodes
        """

        self.map_obstacle = map_obstacle
        self.main_graph = main_graph

        self.sight_range = self.calculate_sight_range()

        self.top_left_y = None
        self.top_left_x = None
        self.bottom_right_y = None
        self.bottom_right_x = None
        self.height = None
        self.width = None
        self.size = self.calculate_size()

        # nodes specific to this threat zone
        self.nodes = []

    def calculate_size(self):
        """
        Calculate the bounds of the threat zone based on the map obstacle.
        Returns the top left corner (y, x) and the bottom right corner (y, x)
        in the form of ((y, x), (y, x), height, width).
        """
        top_left_y = 0
        top_left_x = 0

        bottom_right_y = 1
        bottom_right_x = 1

        # TODO: calculate the correct bounds of the threat zone.

        raise NotImplementedError

        # if there is a sight_range for this map_obstacle then increase the size of the zone.
        if self.sight_range > 0:
            top_left_y += self.sight_range
            top_left_x += self.sight_range
            bottom_right_y += self.sight_range
            bottom_right_x += self.sight_range

        top_left = (top_left_y, top_left_x)
        bottom_right = (bottom_right_y, bottom_right_x)

        height = bottom_right_y - top_left_y
        width = bottom_right_x - top_left_x

        self.top_left_y = top_left_y
        self.top_left_x = top_left_x
        self.bottom_right_y = bottom_right_y
        self.bottom_right_x = bottom_right_x
        self.height = height
        self.width = width

        return (top_left, bottom_right, height, width)

    def is_player_near(self, y, x):
        """
        Applies a boundary of one around the threat zone, then checks if the
        player is inside. This is how the threatzone activates to calculate an
        updated graph or set of penalties for each step.
        """
        y_condition = (self.top_left_y - 1) <= y < (self.bottom_right_y + 1)
        x_condition = (self.top_left_x - 1) <= x < (self.bottom_right_x + 1)
        return y_condition and x_condition

    def check_map_obstacle_has_sight(self):
        """
        Determines if the map object has the sight feature.
        """
        return self.map_obstacle.sight_range > 0

    def calculate_sight_range(self):
        """
        Calculates the range that the object is able to see.
        """
        if not self.check_map_obstacle_has_sight():
            return 0
        else:
            return self.map_obstacle.sight_range

    def get_current_facing_direction(self, DIRECTIONS=DIRECTIONS):
        """
        Get the current facing direction of the map_obstacle.
        """
        return self.map_obstacle.get_current_facing_direction(DIRECTIONS=DIRECTIONS)

    # this isn't used anywhere yet
    def is_map_obstacle_in_screen_range(self):
        """
        Determines if the map_obstacle is within the bounds of whatever is on
        screen at the moment. If the object is of a type that is capable of
        moving, and it is not on screen, then it is not moving.
        """
        raise NotImplementedError

    def mark_nodes_as_members_of_threat_zone(self):
        """
        Based on the nodes in this threat zone, mark each main graph's nodes as
        members of this threat zone.
        """

        for y in range(self.top_left_y, self.top_left_y + self.height):
            for x in range(self.top_left_x, self.top_left_x + self.width):
                main_node = self.main_graph[y][x]
                main_node.threat_zones.add(self)

                self.nodes.append(main_node)

    def update_obstacle_location(self):
        """
        Updates which node has the obstacle. This does not recompute the graph
        based on this new information.

        Each threat zone is responsible for updating its own map objects. So
        there will never be a time when the current x value attached to the
        map_obstacle does not represent the actual previous location.
        """

        # find the previous location of the obstacle
        old_y = self.map_obstacle.y
        old_x = self.map_obstacle.x

        # remove it from the main graph
        self.main_graph[old_y][old_x].contents.remove(self.map_obstacle)

        # get the latest location
        self.map_obstacle.update_location()
        (new_y, new_x) = (self.map_obstacle.y, self.map_obstacle.x)

        # add it back into the main graph
        self.main_graph[new_y][new_x].contents.add(self.map_obstacle)

        # update the map obstacle (not necessary, but it doesn't hurt)
        self.map_obstacle.y = new_y
        self.map_obstacle.x = new_x

    def is_node_in_threat_zone(self, y, x):
        """
        Checks if the node is in the range of the threat zone.
        """
        y_condition = self.top_left_y <= y < self.top_left_y + self.height
        x_condition = self.top_left_x <= x < self.top_left_x + self.width
        return y_condition and x_condition

    def is_node_in_sight_range(self, y, x, skip_range_check=False):
        """
        Checks if the node is in the sight range of the threat.
        """
        if not skip_range_check:
            if not self.is_node_in_threat_zone(y, x):
                return False

        if self.sight_range == 0:
            return False

        # TODO: sight range can be blocked by collidable map objects. But this
        # node wouldn't be in the threat zone anyway.
        y_condition = self.map_obstacle.y == y
        x_condition = self.map_obstacle.x == x

        # this probably only happens if the player warps to the exact spot
        if y_condition and x_condition:
            raise Exception(
                "Don't know the meaning of being on top of the map_obstacle."
            )

        # check if y or x matches the map object
        return y_condition or x_condition

    def is_node_in_active_sight_range(self,
                                      y,
                                      x,
                                      skip_sight_range_check=False,
                                      skip_range_check=False,
                                      DIRECTIONS=DIRECTIONS):
        """
        Checks if the node has active sight range lock.
        """

        if not skip_sight_range_check:
            # can't be in active sight range if not in sight range
            if not self.is_in_sight_range(y, x, skip_range_check=skip_range_check):
                return False

        y_condition = self.map_obstacle.y == y
        x_condition = self.map_obstacle.x == x

        # this probably only happens if the player warps to the exact spot
        if y_condition and x_condition:
            raise Exception(
                "Don't know the meaning of being on top of the map_obstacle."
            )

        current_facing_direction = self.get_current_facing_direction(DIRECTIONS=DIRECTIONS)

        if current_facing_direction not in DIRECTIONS.keys():
            raise Exception(
                "Invalid direction."
            )

        if current_facing_direction in [DIRECTIONS["UP"], DIRECTIONS["DOWN"]]:
            # map_obstacle is looking up/down but player doesn't match y
            if not y_condition:
                return False

            if current_facing_direction == DIRECTIONS["UP"]:
                return y < self.map_obstacle.y
            elif current_facing_direction == DIRECTIONS["DOWN"]:
                return y > self.map_obstacle.y
        else:
            # map_obstacle is looking left/right but player doesn't match x
            if not x_condition:
                return False

            if current_facing_direction == DIRECTIONS["LEFT"]:
                return x < self.map_obstacle.x
            elif current_facing_direction == DIRECTIONS["RIGHT"]:
                return x > self.map_obstacle.x

    def calculate_node_cost(self, y, x, consider_sight_range=True, PENALTIES=PENALTIES):
        """
        Calculates the cost of the node w.r.t this threat zone. Turn off
        consider_sight_range when not in the threat zone.
        """
        penalty = 0

        # The node is probably in the threat zone because otherwise why would
        # this cost function be called? Only the nodes that are members of the
        # current threat zone would have a reference to this threat zone and
        # this function.
        if not self.is_node_in_threat_zone(y, x):
            penalty += PENALTIES["NONE"]

            # Additionally, if htis codepath is ever hit, the other node cost
            # function will have already used the "NONE" penalty, so this would
            # really be doubling the penalty of the node..
            raise Exception(
                "Didn't expect to calculate a non-threat-zone node's cost, "
                "since this is a threat zone function."
            )
        else:
            penalty += PENALTIES["THREAT_ZONE"]

            if consider_sight_range:
                if self.is_node_in_sight_range(y, x, skip_range_check=True):
                    penalty += PENALTIES["SIGHT_RANGE"]

                    params = {
                        "skip_sight_range_check": True,
                        "skip_range_check": True,
                    }

                    active_sight_range = self.is_node_in_active_sight_range(y, x, **params)

                    if active_sight_range:
                        penalty += PENALTIES["ACTIVE_SIGHT_RANGE"]

        return penalty

def create_graph(some_map):
    """
    Creates the array of nodes representing the in-game map.
    """

    map_height = some_map.height
    map_width = some_map.width
    map_obstacles = some_map.obstacles

    nodes = [[None] * map_width] * map_height

    # create a node representing each position on the map
    for y in range(0, map_height):
        for x in range(0, map_width):
            position = (y, x)

            # create a node describing this position
            node = Node(position=position)

            # store it on the graph
            nodes[y][x] = node

    # look through all moving characters, non-moving characters, and items
    for map_obstacle in map_obstacles:
        # all characters must start somewhere
        node = nodes[map_obstacle.y][map_obstacle.x]

        # store the map_obstacle on this node.
        node.contents.add(map_obstacle)

        # only create threat zones for moving/turning entities
        if map_obstacle.can_move() or map_obstacle.can_turn_without_moving():
            threat_zone = ThreatZone(map_obstacle, nodes, some_map)
            threat_zone.mark_nodes_as_members_of_threat_zone()

    some_map.nodes = nodes

    return nodes

class Map(object):
    """
    The ``Map`` class provides an interface for reading the currently loaded
    map.
    """

    def __init__(self, cry, parsed_map, height, width, map_group_id, map_id, config=config):
        """
        :param cry: pokemon crystal emulation interface
        :type cry: crystal
        """
        self.config = config
        self.cry = cry

        self.threat_zones = set()
        self.obstacles = set()

        self.parsed_map = parsed_map
        self.map_group_id = map_group_id
        self.map_id = map_id
        self.height = height
        self.width = width

    def travel_to(self, destination_location):
        """
        Does path planning and figures out the quickest way to get to the
        destination.
        """
        raise NotImplementedError

    @staticmethod
    def from_rom(cry, address):
        """
        Loads a map from bytes in ROM at the given address.

        :param cry: pokemon crystal wrapper
        """
        raise NotImplementedError

    @staticmethod
    def from_wram(cry):
        """
        Loads a map from bytes in WRAM.

        :param cry: pokemon crystal wrapper
        """
        raise NotImplementedError

    def draw_path(self, path):
        """
        Draws a path on an image of the current map. The path must be an
        iterable of nodes to visit in (y, x) format.
        """
        palettes = pokemontools.map_gfx.read_palettes(self.config)
        map_image = pokemontools.map_gfx.draw_map(self.map_group_id, self.map_id, palettes, show_sprites=True, config=self.config)

        for coordinates in path:
            y = coordinates[0]
            x = coordinates[1]

            some_image = Image.new("RGBA", (32, 32))
            draw = ImageDraw.Draw(some_image, "RGBA")
            draw.rectangle([(0, 0), (32, 32)], fill=(0, 0, 0, 127))

            target = [(x * 4, y * 4), ((x + 32) * 4, (y + 32) * 4)]

            map_image.paste(some_image, target, mask=some_image)

        return map_image

class PathPlanner(object):
    """
    Generic path finding implementation.
    """

    def __init__(self, some_map, initial_location, target_location):
        self.some_map = some_map
        self.initial_location = initial_location
        self.target_location = target_location

    def plan(self):
        """
        Runs the path planner and returns a list of positions making up the
        path.
        """
        return [(0, 0), (1, 0), (1, 1), (1, 2), (1, 3)]

def plan_and_draw_path_on(map_group_id=1, map_id=1, initial_location=(0, 0), final_location=(2, 2), config=config):
    """
    An attempt at an entry point. This hasn't been sufficiently considered yet.
    """
    initial_location = (0, 0)
    final_location = (2, 2)
    map_group_id = 1
    map_id = 1

    pokemontools.crystal.cachably_parse_rom()
    pokemontools.map_gfx.add_pokecrystal_paths_to_configuration(config)

    # get the map based on data from the rom
    parsed_map = pokemontools.crystal.map_names[map_group_id][map_id]["header_new"]

    # convert this map into a different structure
    current_map = Map(cry=None, parsed_map=parsed_map, height=parsed_map.height.byte, width=parsed_map.width.byte, map_group_id=map_group_id, map_id=map_id, config=config)

    # make a graph based on the map data
    nodes = create_graph(current_map)

    # make an instance of the planner implementation
    planner = PathPlanner(current_map, initial_location, final_location)

    # Make that planner do its planning based on the current configuration. The
    # planner should be callable in the future and still have
    # previously-calculated state, like cached pre-computed routes or
    # something.
    path = planner.plan()

    # show the path on the map
    drawn = current_map.draw_path(path)

    return drawn
