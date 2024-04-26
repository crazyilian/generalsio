from .constants import *


class Tile(object):
    def __init__(self, gamemap, x, y):
        # Public Properties
        self.x = x  # Integer X Coordinate
        self.y = y  # Integer Y Coordinate
        self.tile = TILE_FOG  # Integer Tile Type (TILE_OBSTACLE, TILE_FOG, TILE_MOUNTAIN, TILE_EMPTY, or player_ID)
        self.turn_captured = 0  # Integer Turn Tile Last Captured
        self.turn_held = 0  # Integer Last Turn Held
        self.army = 0  # Integer Army Count
        self.isCity = False  # Boolean isCity
        self.isSwamp = False  # Boolean isSwamp
        self.isGeneral = False  # Boolean isGeneral

        # Private Properties
        self._map = gamemap  # Pointer to Map Object
        self._general_index = -1  # Player Index if tile is a general

    def __repr__(self):
        return "(%2d,%2d)[%2d,%3d]" % (self.x, self.y, self.tile, self.army)

    '''def __eq__(self, other):
            return (other != None and self.x==other.x and self.y==other.y)'''

    def __lt__(self, other):
        return self.army < other.army

    def setNeighbors(self, gamemap):
        self._map = gamemap
        self._setNeighbors()

    def setIsSwamp(self, isSwamp):
        self.isSwamp = isSwamp

    def update(self, gamemap, tile, army, isCity=False, isGeneral=False):
        self._map = gamemap

        if self.tile < 0 or tile >= TILE_MOUNTAIN or (tile < TILE_MOUNTAIN and self.isSelf()):  # Tile should be updated
            if (tile >= 0 or self.tile >= 0) and self.tile != tile:  # Remember Discovered Tiles
                self.turn_captured = gamemap.turn
                if self.tile >= 0:
                    gamemap.tiles[self.tile].remove(self)
                if tile >= 0:
                    gamemap.tiles[tile].add(self)
            if tile == gamemap.player_index:
                self.turn_held = gamemap.turn
            if self.tile != tile and tile < 0:
                self._setNeighbors()
                for n in self._neighbors:
                    n._setNeighbors()
            self.tile = tile

        if self.army == 0 or army > 0 or tile >= TILE_MOUNTAIN or self.isSwamp:  # Remember Discovered Armies
            self.army = army

        if isCity:
            self.isCity = True
            self.isGeneral = False
            if self not in gamemap.cities:
                gamemap.cities.append(self)
            if self._general_index != -1 and self._general_index < 8:
                gamemap.generals[self._general_index] = None
                self._general_index = -1
        elif isGeneral:
            self.isGeneral = True
            gamemap.generals[tile] = self
            self._general_index = self.tile

    ################################ Tile Properties ################################

    def neighbors(self, cities=False, swamps=False, obstacles=False):
        neighbors = []
        for tile in self._neighbors:
            if tile.isCity and not cities:
                continue
            if tile.isSwamp and not swamps:
                continue
            if tile.tile == TILE_OBSTACLE and not obstacles:
                continue
            neighbors.append(tile)
        return neighbors

    def isEmpty(self):
        return self.tile == TILE_EMPTY

    def isSelf(self):
        return self.tile == self._map.player_index

    ################################ PRIVATE FUNCTIONS ################################

    def _setNeighbors(self):
        x = self.x
        y = self.y

        neighbors = []
        for dy, dx in DIRECTIONS:
            if self._map.isValidPosition(x + dx, y + dy):
                tile = self._map.grid[y + dy][x + dx]
                neighbors.append(tile)

        self._neighbors = neighbors
        return neighbors
