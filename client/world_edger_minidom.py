#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##    Copyeast © 2012 Wushin <pasekei@gmail.com>
##
##    This file is part of The Mana World
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 2 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

## Notes: World Map connects on the edges

from __future__ import print_function

import time
import os
import re
import sys
import csv
import posixpath
import xml.dom.minidom
from xml.dom.minidom import getDOMImplementation

EDGE_COLLISION = 20
OUTER_LIMITX = 9
OUTER_LIMITY = 9
CLIENT_MAPS = 'maps'
MAP_RE = re.compile(r'^\d{2}-\d{2}-\d{2}-\d{2}-\d{2}(\.tmx)?$')
LAYERS = ['Ground', 'Fringe', 'Over', 'Collision']

class parseMap:

    def __init__(self, map):
        self.layername = ""
        self.data = ""
        self.layercopy = {}
        self.layeredges = {'BaseLayers': {}}
        self.mapdata = xml.dom.minidom.parse(map)
        self.handleMap()

    def handleMap(self):
        maptags = self.mapdata.documentElement
        self.mapwidth = int(maptags.attributes['width'].value)
        self.mapheight = int(maptags.attributes['height'].value)
        self.handleMapProperties()
        self.handleTileSets()
        self.handleLayers()
        self.handleObjects()
        return

    def handleMapProperties(self):
        self.layeredges['mapProperties'] = self.mapdata.getElementsByTagName("property")
        return

    def handleTileSets(self):
        self.layeredges['Tilesets'] = self.mapdata.getElementsByTagName("tileset")
        return

    def handleLayers(self):
        layers = self.mapdata.getElementsByTagName("layer")
        for layer in layers:
            self.layername = layer.attributes['name'].value
            self.layerData = layer.getElementsByTagName("data")
            if(self.layername != 'Collision'):
                self.handleLayerData()
            self.layercopy[self.layername] = self.data
        return

    def handleLayerData(self):
        self.data = self.layerData[0].firstChild.nodeValue
        self.findTilesToCopy()
        return

    def handleObjects(self):
        self.layeredges['objects'] = self.mapdata.getElementsByTagName("objectgroup")
        return

    def findTilesToCopy(self):
        self.layeredges['BaseLayers'][self.layername] = {'north': {}, 'south': {}, 'west': {}, 'east': {}}
        reader = csv.reader(self.data.strip().split('\n'), delimiter=',')
        for row in reader:
            self.layeredges['BaseLayers'][self.layername]['west'][reader.line_num] = row[EDGE_COLLISION:(EDGE_COLLISION*2)]
            self.layeredges['BaseLayers'][self.layername]['east'][reader.line_num] = row[(self.mapwidth - (EDGE_COLLISION*2)):(self.mapwidth - EDGE_COLLISION)]
            if(reader.line_num in range(EDGE_COLLISION,((EDGE_COLLISION*2) + 1))):
                self.layeredges['BaseLayers'][self.layername]['south'][reader.line_num] = row
            if(reader.line_num in range((self.mapheight - (EDGE_COLLISION*2)),(self.mapheight - (EDGE_COLLISION - 1)))):
                self.layeredges['BaseLayers'][self.layername]['north'][reader.line_num] = row

class copyMap:

    def __init__(self, map, layeredges = {}, direction = False):
        self.tilesets = {}
        self.data = {}
        self.layercopy = {}
        self.layeredges = layeredges
        self.layeredges['LayerCopy'] = {}
        self.direction = direction
        self.mapdata = xml.dom.minidom.parse(map)
        self.tmxout = getDOMImplementation().createDocument(None, 'map', None)
        self.handleMap()

    def handleMap(self):
        self.maptags = self.mapdata.documentElement
        self.mapwidth = int(self.maptags.attributes['width'].value)
        self.mapheight = int(self.maptags.attributes['height'].value)
        self.tmxout.documentElement.setAttribute(u'orientation', u'orthogonal')
        self.tmxout.documentElement.setAttribute(u'width', str(self.mapwidth))
        self.tmxout.documentElement.setAttribute(u'height', str(self.mapheight))
        self.tmxout.documentElement.setAttribute(u'tilewidth', u'32')
        self.tmxout.documentElement.setAttribute(u'tileheight', u'32')
        self.handleMapProperties()
        self.handleTileSets()
        self.handleLayers()
        self.handleObjects()
        return

    def handleMapProperties(self):
        mapProperties = self.mapdata.getElementsByTagName("property")
        newMapProps = self.tmxout.createElement("properties")
        for mapProp in mapProperties:
            newProp = self.tmxout.createElement("property")
            newProp.setAttribute(u'name', str(mapProp.attributes['name'].value))
            newProp.setAttribute(u'value', str(mapProp.attributes['value'].value))
            newMapProps.appendChild(newProp)
        self.tmxout.documentElement.appendChild(newMapProps)
        return

    def handleTileSets(self):
        self.xmlTileSets = self.mapdata.getElementsByTagName("tileset")
        tileGids = []
        for tileSet in self.xmlTileSets:
            newTileSet = self.tmxout.createElement('tileset')
            newTileSet.attributes['firstgid'] = tileSet.attributes['firstgid'].value
            newTileSet.attributes['source'] = tileSet.attributes['source'].value
            self.tmxout.documentElement.appendChild(newTileSet)
            tileGids.append(tileSet.attributes['firstgid'].value)
        # Append Each Tileset
        for tileSet in self.layeredges['Tilesets']:
            newTileSet = self.tmxout.createElement('tileset')
            # Pull up and Offset self.layerEdges All base on tileset modifications
            if not tileSet.attributes['firstgid'].value in tileGids:
                newTileSet.attributes['firstgid'] = tileSet.attributes['firstgid'].value
                newTileSet.attributes['source'] = tileSet.attributes['source'].value
                self.tmxout.documentElement.appendChild(newTileSet)
        return

    def handleLayers(self):
        layers = self.mapdata.getElementsByTagName("layer")
        for layer in layers:
            self.layeredges['LayerCopy'][layer.attributes['name'].value] = layer.getElementsByTagName("data")[0].childNodes[0].nodeValue
        self.handleLayerData()
        return

    def handleLayerData(self):
        layersMissing = set(self.layeredges['BaseLayers'].keys()).difference(set(self.layeredges['LayerCopy'].keys()))
        layersNeeded = sorted(list(set(self.layeredges['LayerCopy'].keys()).union(set(self.layeredges['BaseLayers'].keys()))))
        for layerMissed in layersMissing:
            fakedData = ((','.join(['0'] * self.mapwidth) + ',').join(['\n'] * (self.mapheight + 1)))
            self.layeredges['LayerCopy'][layerMissed] = fakedData[:-2] + "\n"
        for mapLayer in LAYERS:
            for mapLayerNeed in layersNeeded:
                if (re.search(mapLayer, mapLayerNeed)):
                    newLayer = self.tmxout.createElement('layer')
                    newLayer.attributes['name'] = mapLayerNeed
                    newLayer.attributes['width'] = str(self.mapwidth)
                    newLayer.attributes['height'] = str(self.mapheight)
                    newData = self.tmxout.createElement('data')
                    newData.attributes['encoding'] = 'csv'
                    self.data['LayerCopy'] = self.layeredges['LayerCopy'][mapLayerNeed]
                    if mapLayerNeed in self.layeredges['BaseLayers'].keys():
                        self.data['BaseLayers'] = self.layeredges['BaseLayers'][mapLayerNeed]
                        self.mapCopyTiles()
                    else:
                        self.newMapData = self.layeredges['LayerCopy'][mapLayerNeed]
                    newDataValue = self.tmxout.createTextNode(self.newMapData)
                    newData.appendChild(newDataValue)
                    newLayer.appendChild(newData)
                    self.tmxout.documentElement.appendChild(newLayer)
        return

    def handleObjects(self):
        mapObjects = self.mapdata.getElementsByTagName("objectgroup")
        for mapObject in mapObjects:
            self.tmxout.documentElement.appendChild(mapObject)
        return

    def mapCopyTiles(self):
        reader = csv.reader(self.data['LayerCopy'].strip().split('\n'), delimiter=',')
        copiedrows = ""
        for row in reader:
            if(reader.line_num in range(1,(EDGE_COLLISION + 1)) and self.direction == 'north'):
                copiedrows += (','.join(self.data['BaseLayers']['north'][(reader.line_num + (self.mapheight - (EDGE_COLLISION*2)))][:-1])) + ","
            elif(reader.line_num in range((self.mapheight - (EDGE_COLLISION - 1)),(self.mapheight + 1)) and self.direction == 'south'):
                if(reader.line_num == self.mapheight):
                    copiedrows += (','.join(self.data['BaseLayers']['south'][(reader.line_num - (self.mapheight - (EDGE_COLLISION*2)))][:-1]))
                else:
                    copiedrows += (','.join(self.data['BaseLayers']['south'][(reader.line_num - (self.mapheight - (EDGE_COLLISION*2)))][:-1])) + ","
            elif(self.direction == 'west'):
                westrow = self.data['BaseLayers']['west'][reader.line_num]
                if(reader.line_num == self.mapheight):
                    copiedrows += (','.join(row[:(self.mapwidth - EDGE_COLLISION)] + westrow))
                else:
                    copiedrows += (','.join(row[:(self.mapwidth - EDGE_COLLISION)] + westrow)) + ","
            elif(self.direction == 'east'):
                eastrow = self.data['BaseLayers']['east'][reader.line_num]
                copiedrows += (','.join(eastrow + row[EDGE_COLLISION:]))
            else:
                copiedrows += (','.join(row))
            copiedrows += "\n"
        self.newMapData = "\n" + copiedrows
        return

def main(argv):
    _, client_data = argv
    tmx_dir = posixpath.join(client_data, CLIENT_MAPS)

    for arg in os.listdir(tmx_dir):
        base, ext = posixpath.splitext(arg)

        if ext == '.tmx' and MAP_RE.match(base):
            tmx = posixpath.join(tmx_dir, arg)
            # Create Tileset Mapping
            mainMapData = parseMap(tmx)
            (world,mapx,mapy,level,room) = (base.split('-'))
            # World Map loops onto itself
            mapxwest = int(mapx) - 1
            mapxeast = int(mapx) + 1
            if (int(mapx) == 0):
                mapxwest = OUTER_LIMITX
            elif (int(mapx) == OUTER_LIMITX):
                mapxeast = 0

            mapynorth = int(mapy) - 1
            mapysouth = int(mapy) + 1
            if (int(mapy) == 0):
                mapynorth = OUTER_LIMITY
            if (int(mapy) == OUTER_LIMITY):
                mapysouth = 0
            
            # Get/Open/Parse Adjacent Maps Possibly make a map property
            adjacentmaps = {'south': "%s-%s-%02d-%s-%s.tmx" % (world, mapx, mapynorth, level, room), 'north': "%s-%s-%02d-%s-%s.tmx" % (world, mapx, mapysouth, level, room), 'west': "%s-%02d-%s-%s-%s.tmx" % (world, mapxwest, mapy, level, room), 'east': "%s-%02d-%s-%s-%s.tmx" % (world, mapxeast, mapy, level, room)}
            print ("base map: %s.tmx" % (base))
            for mapdirection in adjacentmaps:
                #print ("%s map: %s" % (mapdirection, adjacentmaps[mapdirection]))
                mapname = posixpath.join(tmx_dir, adjacentmaps[mapdirection])
                MapData = copyMap(mapname, mainMapData.layeredges, mapdirection)
                newxml = MapData.tmxout.toprettyxml(encoding="utf-8")
                map_file = open(mapname, "w")
                map_file.write(newxml)
                map_file.close()

if __name__ == '__main__':
    main(sys.argv)
