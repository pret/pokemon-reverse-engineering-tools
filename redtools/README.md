# redtools

The `redtools` are mostly python files that were removed from the
[pokered](https://github.com/iimarckus/pokered) project.

# Why was this removed from pokered?

Originally, `extras/` was where all tools were put in the pokered project.
These utilities and tools are for disassembling the ROM, extracting data, and
prettifying text.

When the [pokecrystal](https://github.com/kanzure/pokecrystal) project started,
many of these tools were copied into pokecrystal. This was a mistake because it
meant that there were two copies of the same python source code in two places.
This causes all sorts of problems because if a bug is found in one repository,
it's really hard to figure out if the bug applies to the other project, or to
keep track of where the bugs have been fixed or not fixed. The effects are
duplication of effort, less progress overall, and so on.

# Moving forward

These files should be merged into the `pokemontools/` module. More tests need
to be written to make sure some of the functionality has been preserved.

# What about just deleting everything?

Everything in here could be deleted without negatively impacting pokered
builds. But there will be some lost effort, like the pretty text inserter.

# Things worth keeping or redoing

* pretty text - this is a command line tool that parses text from the ROM at a
  given address, and dumps out pretty-formatted asm ready for insertion.

* gbz80disasm - might have one or two fixes ahead of
  pokemontools/gbz80disasm.py, but is significantly inferior in general.

* romviz and romvisualizer - makes an animated gif of progress removing
  INCBINs. Needs to be rewritten to follow INCLUDEs.

* redrle.c - pokered town maps tool

* maybe other things
