"""
Generic functions that should be reusable anywhere in pokemontools.
"""
import os

def index(seq, f):
    """
    return the index of the first item in seq
    where f(item) == True.
    """
    return next((i for i in xrange(len(seq)) if f(seq[i])), None)

def grouper(some_list, count=2):
    """
    splits a list into sublists

    given: [1, 2, 3, 4]
    returns: [[1, 2], [3, 4]]
    """
    return [some_list[i:i+count] for i in range(0, len(some_list), count)]

def flattener(x):
    """
    flattens a list of sublists into just one list (generator)
    """
    try:
        it = iter(x)
    except TypeError:
        yield x
    else:
        for i in it:
            for j in flattener(i):
                yield j

def flatten(x):
    """
    flattens a list of sublists into just one list
    """
    return list(flattener(x))

def mkdir_p(path):
    """
    Make a directory at a given path.
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise exc
