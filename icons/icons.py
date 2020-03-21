# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2017 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####

import os
import bpy
import bpy.utils.previews

renderman_icon_collections = {}
renderman_icons_loaded = False


def load_icons():
    global renderman_icon_collections
    global renderman_icons_loaded

    if renderman_icons_loaded:
        return renderman_icon_collections["main"]

    custom_icons = bpy.utils.previews.new()

    icons_dir = os.path.join(os.path.dirname(__file__))

    for f in os.listdir(icons_dir):
        if not f.endswith('.png'):
            continue
        custom_icons.load(f, os.path.join(icons_dir, f), 'IMAGE')
        

    # FIXME: Not sure why this is needed
    # Without it, icons don't seem to show up?
    for img in custom_icons.values():
        x = img.icon_size[0]
        y = img.icon_size[1]

    renderman_icon_collections["main"] = custom_icons
    renderman_icons_loaded = True

    return renderman_icon_collections["main"]


def clear_icons():
    global renderman_icons_loaded
    for icon in renderman_icon_collections.values():
        bpy.utils.previews.remove(icon)
    renderman_icon_collections.clear()
    renderman_icons_loaded = False
