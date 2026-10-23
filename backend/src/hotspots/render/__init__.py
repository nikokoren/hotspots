"""Rendering support for the TRMNL recipe.

The recipe draws the map itself (Liquid + TRMNL framework). This package only
prepares what it needs: view definitions, world-view marker positions in
percent of the map box, and marker sizes and shades. It consumes
models.Marker, never raw source data.
"""
