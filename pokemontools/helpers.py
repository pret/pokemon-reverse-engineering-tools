"""
Generic functions that should be reusable anywhere in pokemontools.
"""

def index(seq, f):
    """return the index of the first item in seq
    where f(item) == True."""
    return next((i for i in xrange(len(seq)) if f(seq[i])), None)

def grouper(some_list, count=2):
    """splits a list into sublists
    given: [1, 2, 3, 4]
    returns: [[1, 2], [3, 4]]"""
    return [some_list[i:i+count] for i in range(0, len(some_list), count)]
