# -*- coding: utf-8 -*-
"""
This file constructs a networkx.DiGraph object called graph, which can be used
to find the shortest path of keypresses on the keyboard to type a word.
"""

import os
import itertools
import networkx

graph = networkx.DiGraph()

# load graph data from file
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keyboard.data")
graph_data = open(data_path, "r").read()

for line in graph_data.split("\n"):
    if line == "":
        continue
    elif line[0] == "#":
        continue

    (node1, node2, edge_name) = line.split(" ")
    graph.add_edge(node1, node2, key=edge_name)

    #print "Adding edge ("+edge_name+") "+node1+" -> "+node2

def shortest_path(node1, node2):
    """
    Figures out the shortest list of button presses to move from one letter to
    another.
    """
    buttons = []
    last = None
    path = networkx.shortest_path(graph, node1, node2)
    for each in path:
        if last != None:
            buttons.append(convert_nodes_to_button_press(last, each))
        last = each
    return buttons
    #return [convert_nodes_to_button_press(node3, node4) for (node3, node4) in zip(*(iter(networkx.shortest_path(graph, node1, node2)),) * 2)]

def convert_nodes_to_button_press(node1, node2):
    """
    Determines the button necessary to switch from node1 to node2.
    """
    print "getting button press for state transition: " + node1 + " -> " + node2
    return graph.get_edge_data(node1, node2)["key"]

def plan_typing(text, current="A"):
    """
    Plans a sequence of button presses to spell out the given text.
    """
    buttons = []
    for target in text:
        if target == current:
            buttons.append("a")
        else:
            print "Finding the shortest path between " + current + " and " + target
            more_buttons = shortest_path(current, target)
            buttons.extend(more_buttons)
            buttons.append("a")
            current = target
    return buttons
