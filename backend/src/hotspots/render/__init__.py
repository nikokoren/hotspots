"""Rendering support for the TRMNL recipe.

The recipe draws the map itself (Liquid + TRMNL framework classes). This
package only prepares what it needs: a land-mask PNG per view, and marker
positions in percent of the map box. It consumes models.Marker, never raw
source data.
"""
