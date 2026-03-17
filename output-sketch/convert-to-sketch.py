#!/usr/bin/env python3
"""
HTML Sketch → Sketch (.sketch) File Converter
===============================================
Parses HTML/CSS UI sketches and generates valid Sketch 43+ format files.
The .sketch files can be opened in Sketch, imported into Figma, Penpot, or Lunacy.

Usage:
    python convert-to-sketch.py
"""

import os
import sys
import json
import re
import uuid
import zipfile
from pathlib import Path

# ============================================================
# SECTION 1: Sketch Format Utilities
# ============================================================

def new_uuid():
    """Generate a new UUID string for Sketch objects."""
    return str(uuid.uuid4()).upper()


def hex_to_sketch_color(hex_str, alpha=1.0):
    """Convert hex color (#RRGGBB or #RGB) to Sketch color dict."""
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    if len(hex_str) < 6:
        hex_str = hex_str.ljust(6, '0')
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"_class": "color", "alpha": alpha, "blue": b, "green": g, "red": r}


def rgba_to_sketch_color(rgba_str):
    """Convert rgba(r,g,b,a) or rgb(r,g,b) to Sketch color dict."""
    m = re.match(
        r'rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+))?\s*\)',
        rgba_str
    )
    if m:
        r = float(m.group(1)) / 255.0
        g = float(m.group(2)) / 255.0
        b = float(m.group(3)) / 255.0
        a = float(m.group(4)) if m.group(4) else 1.0
        return {"_class": "color", "alpha": a, "blue": b, "green": g, "red": r}
    return {"_class": "color", "alpha": 1.0, "blue": 0.5, "green": 0.5, "red": 0.5}


def parse_css_color(value):
    """Parse any CSS color value to a Sketch color dict."""
    if not value:
        return hex_to_sketch_color('#888888')
    value = value.strip()
    if value.startswith('#'):
        return hex_to_sketch_color(value)
    if value.startswith('rgb'):
        return rgba_to_sketch_color(value)
    named = {
        'white': '#ffffff', 'black': '#000000',
        'transparent': '#00000000',
    }
    if value.lower() in named:
        return hex_to_sketch_color(named[value.lower()])
    return hex_to_sketch_color('#888888')


def with_alpha(color, alpha):
    """Return a copy of a Sketch color with a different alpha."""
    return {**color, "alpha": alpha}


# ============================================================
# SECTION 2: Sketch JSON Object Factories
# ============================================================

def make_rect(x, y, w, h):
    return {
        "_class": "rect",
        "constrainProportions": False,
        "height": float(h),
        "width": float(w),
        "x": float(x),
        "y": float(y)
    }


def make_export_options():
    return {
        "_class": "exportOptions",
        "includedLayerIds": [],
        "layerOptions": 0,
        "shouldTrim": False,
        "exportFormats": []
    }


def make_base_layer(cls, name, x, y, w, h):
    """Create the base layer structure common to all layer types."""
    return {
        "_class": cls,
        "do_objectID": new_uuid(),
        "booleanOperation": -1,
        "isFixedToViewport": False,
        "isFlippedHorizontal": False,
        "isFlippedVertical": False,
        "isLocked": False,
        "isVisible": True,
        "layerListExpandedType": 0,
        "name": name,
        "nameIsFixed": True,
        "resizingConstraint": 63,
        "resizingType": 0,
        "rotation": 0,
        "shouldBreakMaskChain": False,
        "exportOptions": make_export_options(),
        "frame": make_rect(x, y, w, h),
        "clippingMaskMode": 0,
        "hasClippingMask": False,
    }


def make_style(fills=None, borders=None, shadows=None):
    return {
        "_class": "style",
        "endMarkerType": 0,
        "miterLimit": 10,
        "startMarkerType": 0,
        "windingRule": 1,
        "fills": fills or [],
        "borders": borders or [],
        "shadows": shadows or [],
        "innerShadows": []
    }


def make_fill(color, fill_type=0):
    return {
        "_class": "fill",
        "isEnabled": True,
        "fillType": fill_type,
        "color": color
    }


def make_border(color, thickness=1, position=1):
    return {
        "_class": "border",
        "isEnabled": True,
        "fillType": 0,
        "color": color,
        "thickness": float(thickness),
        "position": position  # 0=center, 1=inside, 2=outside
    }


def make_shadow(color, x=0, y=4, blur=24, spread=0):
    return {
        "_class": "shadow",
        "isEnabled": True,
        "blurRadius": float(blur),
        "color": color,
        "contextSettings": {
            "_class": "graphicsContextSettings",
            "blendMode": 0,
            "opacity": 1
        },
        "offsetX": float(x),
        "offsetY": float(y),
        "spread": float(spread)
    }


def make_rectangle(name, x, y, w, h, fill_color=None, border_color=None,
                   border_width=1, corner_radius=0, shadows=None):
    """Create a rectangle shape layer."""
    layer = make_base_layer("rectangle", name, x, y, w, h)

    fills = [make_fill(fill_color)] if fill_color else []
    borders = [make_border(border_color, border_width)] if border_color else []
    layer["style"] = make_style(fills=fills, borders=borders, shadows=shadows)

    cr = float(corner_radius)
    layer["edited"] = False
    layer["isClosed"] = True
    layer["pointRadiusBehaviour"] = 1
    layer["fixedRadius"] = cr
    layer["hasConvertedToNewRoundCorners"] = True
    layer["needsConvertionToNewRoundCorners"] = False
    layer["points"] = [
        {"_class": "curvePoint", "cornerRadius": cr,
         "curveFrom": "{0, 0}", "curveMode": 1, "curveTo": "{0, 0}",
         "hasCurveFrom": False, "hasCurveTo": False, "point": "{0, 0}"},
        {"_class": "curvePoint", "cornerRadius": cr,
         "curveFrom": "{1, 0}", "curveMode": 1, "curveTo": "{1, 0}",
         "hasCurveFrom": False, "hasCurveTo": False, "point": "{1, 0}"},
        {"_class": "curvePoint", "cornerRadius": cr,
         "curveFrom": "{1, 1}", "curveMode": 1, "curveTo": "{1, 1}",
         "hasCurveFrom": False, "hasCurveTo": False, "point": "{1, 1}"},
        {"_class": "curvePoint", "cornerRadius": cr,
         "curveFrom": "{0, 1}", "curveMode": 1, "curveTo": "{0, 1}",
         "hasCurveFrom": False, "hasCurveTo": False, "point": "{0, 1}"},
    ]
    return layer


def make_text(name, string, x, y, w, h, font_size=14, font_name="Inter-Regular",
              color=None, alignment=0, line_height=None):
    """Create a text layer."""
    if color is None:
        color = hex_to_sketch_color("#000000")
    if line_height is None:
        line_height = int(font_size * 1.5)

    layer = make_base_layer("text", name, x, y, w, h)

    encoded_attrs = {
        "MSAttributedStringFontAttribute": {
            "_class": "fontDescriptor",
            "attributes": {"name": font_name, "size": float(font_size)}
        },
        "MSAttributedStringColorAttribute": color,
        "paragraphStyle": {
            "_class": "paragraphStyle",
            "alignment": alignment,  # 0=left, 1=right, 2=center
            "maximumLineHeight": float(line_height),
            "minimumLineHeight": float(line_height)
        },
        "kerning": 0
    }

    layer["style"] = make_style()
    layer["style"]["textStyle"] = {
        "_class": "textStyle",
        "verticalAlignment": 0,
        "encodedAttributes": encoded_attrs
    }

    layer["automaticallyDrawOnUnderlyingPath"] = False
    layer["dontSynchroniseWithSymbol"] = False
    layer["lineSpacingBehaviour"] = 2
    layer["textBehaviour"] = 1  # 0=auto width, 1=fixed width
    layer["glyphBounds"] = "{{0, 3}, {%d, %d}}" % (int(w), int(h))
    layer["attributedString"] = {
        "_class": "attributedString",
        "string": string,
        "attributes": [{
            "_class": "stringAttribute",
            "location": 0,
            "length": len(string),
            "attributes": encoded_attrs
        }]
    }
    return layer


def make_group(name, x, y, w, h, layers=None):
    """Create a group layer containing child layers."""
    layer = make_base_layer("group", name, x, y, w, h)
    layer["style"] = make_style()
    layer["layers"] = layers or []
    return layer


def make_artboard(name, w, h, bg_color=None, layers=None):
    """Create an artboard layer."""
    layer = make_base_layer("artboard", name, 0, 0, w, h)
    layer["hasBackgroundColor"] = bg_color is not None
    if bg_color:
        layer["backgroundColor"] = bg_color
    layer["includeBackgroundColorInExport"] = True
    layer["horizontalRulerData"] = {"_class": "rulerData", "base": 0, "guides": []}
    layer["verticalRulerData"] = {"_class": "rulerData", "base": 0, "guides": []}
    layer["layout"] = None
    layer["grid"] = None
    layer["style"] = make_style()
    layer["layers"] = layers or []
    return layer


def make_page(name, artboards=None):
    """Create a page."""
    page = make_base_layer("page", name, 0, 0, 0, 0)
    page["style"] = make_style()
    page["layers"] = artboards or []
    for key in ["clippingMaskMode", "hasClippingMask", "booleanOperation"]:
        page.pop(key, None)
    return page


def make_document(pages):
    """Create the document.json content."""
    return {
        "_class": "document",
        "do_objectID": new_uuid(),
        "colorSpace": 1,
        "currentPageIndex": 0,
        "foreignLayerStyles": [],
        "foreignSymbols": [],
        "foreignTextStyles": [],
        "layerStyles": {"_class": "sharedStyleContainer", "objects": []},
        "layerTextStyles": {"_class": "sharedTextStyleContainer", "objects": []},
        "pages": [
            {
                "_class": "MSJSONFileReference",
                "_ref_class": "MSImmutablePage",
                "_ref": "pages/" + p["do_objectID"]
            }
            for p in pages
        ]
    }


def make_meta(pages):
    """Create the meta.json content."""
    pages_and_artboards = {}
    for p in pages:
        ab_dict = {}
        for layer in p.get("layers", []):
            if layer["_class"] == "artboard":
                ab_dict[layer["do_objectID"]] = {"name": layer["name"]}
        pages_and_artboards[p["do_objectID"]] = {
            "name": p["name"],
            "artboards": ab_dict
        }

    return {
        "commit": "generated-by-converter",
        "pagesAndArtboards": pages_and_artboards,
        "version": 136,
        "compatibilityVersion": 99,
        "app": "com.bohemiancoding.sketch3",
        "autosaved": 0,
        "variant": "NONAPPSTORE",
        "created": {
            "commit": "generated-by-converter",
            "appVersion": "96",
            "build": 0,
            "app": "com.bohemiancoding.sketch3",
            "compatibilityVersion": 99,
            "version": 136,
            "variant": "NONAPPSTORE"
        },
        "saveHistory": ["NONAPPSTORE.96"],
        "appVersion": "96",
        "build": 0
    }


def make_user(pages):
    """Create the user.json content."""
    user = {"document": {"pageListHeight": 110, "pageListCollapsed": 0}}
    for p in pages:
        user[p["do_objectID"]] = {"scrollOrigin": "{0, 0}", "zoomValue": 1}
    return user


# ============================================================
# SECTION 3: CSS Variable Extraction
# ============================================================

def extract_css_vars(html):
    """Extract CSS custom properties from the :root block."""
    css_vars = {}
    root_match = re.search(r':root\s*\{([^}]+)\}', html)
    if root_match:
        block = root_match.group(1)
        for m in re.finditer(r'--([\w-]+)\s*:\s*([^;]+);', block):
            name = m.group(1).strip()
            value = m.group(2).strip()
            css_vars[name] = value
    return css_vars


def get_color(css_vars, *keys):
    """Get a Sketch color from CSS variables, trying multiple key names."""
    for key in keys:
        if key in css_vars:
            val = css_vars[key]
            if val.startswith('#') or val.startswith('rgb'):
                return parse_css_color(val)
    return hex_to_sketch_color('#888888')


def get_radius(css_vars):
    """Get border radius value from CSS variables."""
    val = css_vars.get('radius', '12px')
    m = re.match(r'(\d+)', val)
    return int(m.group(1)) if m else 12


# ============================================================
# SECTION 4: Layout Constants
# ============================================================

ARTBOARD_W = 1440
CONTENT_MAX_W = 1200
CONTENT_X = (ARTBOARD_W - CONTENT_MAX_W) // 2  # 120px


# ============================================================
# SECTION 5: Component Builders
# ============================================================

def build_top_nav(css_vars, nav_items, brand_name="Eco-Nudge", brand_icon="🌿",
                  streak="🔥 3"):
    """Build a horizontal top navigation bar. Returns (group, height)."""
    nav_h = 56
    bg_color = get_color(css_vars, 'surface', 'surface-1')
    border_color = get_color(css_vars, 'border')
    accent = get_color(css_vars, 'accent', 'green-400', 'green-500', 'blue',
                       'primary', 'neon')
    muted = get_color(css_vars, 'text-muted')

    layers = []

    # Background
    layers.append(make_rectangle("Nav BG", 0, 0, ARTBOARD_W, nav_h,
                                 fill_color=bg_color, border_color=border_color))

    # Brand
    layers.append(make_text("Brand Icon", brand_icon, 32, 14, 28, 28,
                            font_size=20, font_name="Inter-Regular", color=accent))
    layers.append(make_text("Brand Name", brand_name, 64, 16, 160, 24,
                            font_size=18, font_name="PlayfairDisplay-Bold",
                            color=accent))

    # Nav links
    link_x = 400
    for i, item in enumerate(nav_items):
        is_active = (i == 0)
        col = accent if is_active else muted
        font = "Inter-SemiBold" if is_active else "Inter-Medium"
        item_w = len(item) * 9 + 16

        if is_active:
            layers.append(make_rectangle(
                f"Active BG: {item}", link_x - 8, 10, item_w, 36,
                fill_color=with_alpha(accent, 0.12), corner_radius=8))

        layers.append(make_text(
            f"Nav: {item}", item, link_x, 18, len(item) * 9, 20,
            font_size=14, font_name=font, color=col))
        link_x += item_w + 16

    # Streak
    sx = ARTBOARD_W - 100
    layers.append(make_rectangle("Streak BG", sx, 12, 64, 32,
                                 fill_color=with_alpha(accent, 0.12),
                                 corner_radius=16))
    layers.append(make_text("Streak", streak, sx + 12, 18, 40, 20,
                            font_size=13, font_name="Inter-SemiBold", color=accent))

    return make_group("Navigation Bar", 0, 0, ARTBOARD_W, nav_h, layers), nav_h


def build_sidebar_nav(css_vars, nav_items, brand_name="Eco-Nudge",
                      brand_icon="🌿", streak="🔥 3"):
    """Build a fixed left sidebar. Returns (group, sidebar_width)."""
    sidebar_w = 240
    sidebar_h = 1024
    bg = get_color(css_vars, 'sidebar-bg')
    txt = get_color(css_vars, 'sidebar-text')
    accent = get_color(css_vars, 'green-400', 'accent')

    layers = []
    layers.append(make_rectangle("Sidebar BG", 0, 0, sidebar_w, sidebar_h,
                                 fill_color=bg))

    # Brand
    layers.append(make_text("Brand Icon", brand_icon, 20, 24, 28, 28,
                            font_size=20, font_name="Inter-Regular", color=accent))
    layers.append(make_text("Brand Name", brand_name, 52, 26, 150, 24,
                            font_size=17, font_name="PlayfairDisplay-Bold",
                            color=accent))

    emojis = ["🍽️", "🤖", "📚", "📊", "⚙️"]
    y = 100
    for i, item in enumerate(nav_items):
        is_active = (i == 0)
        col = accent if is_active else txt

        if is_active:
            layers.append(make_rectangle(
                f"Active BG", 0, y, sidebar_w, 44,
                fill_color=with_alpha(accent, 0.2)))
            layers.append(make_rectangle(
                "Active Border", 0, y, 3, 44, fill_color=accent))

        emoji = emojis[i] if i < len(emojis) else "📌"
        layers.append(make_text(f"Emoji {i}", emoji, 20, y + 12, 20, 20,
                                font_size=15, font_name="Inter-Regular", color=col))
        layers.append(make_text(f"Nav: {item}", item, 48, y + 12, 160, 20,
                                font_size=14,
                                font_name="Inter-SemiBold" if is_active else "Inter-Medium",
                                color=col))
        y += 44

    layers.append(make_text("Streak", streak, 20, sidebar_h - 60, 200, 20,
                            font_size=13, font_name="Inter-SemiBold", color=accent))

    return make_group("Sidebar Navigation", 0, 0, sidebar_w, sidebar_h, layers), sidebar_w


def build_header(css_vars, title, subtitle, y, centered=False,
                 content_x=CONTENT_X):
    """Build the page header. Returns (group, next_y)."""
    accent = get_color(css_vars, 'accent', 'green-400', 'blue', 'primary', 'neon')
    muted = get_color(css_vars, 'text-muted')
    align = 2 if centered else 0
    w = CONTENT_MAX_W

    layers = [
        make_text("Title", title, 0, 0, w, 40, font_size=28,
                  font_name="PlayfairDisplay-Bold", color=accent, alignment=align),
        make_text("Subtitle", subtitle, 0, 44, w, 24, font_size=15,
                  font_name="Inter-Regular", color=muted, alignment=align),
    ]
    return make_group("View Header", content_x, y, w, 72, layers), y + 104


def build_recipe_card(css_vars, card, x, y, w=360, h=340, img_h=180, radius=12):
    """Build a single recipe card group."""
    surface = get_color(css_vars, 'surface', 'surface-1')
    border = get_color(css_vars, 'border')
    text_col = get_color(css_vars, 'text')
    muted = get_color(css_vars, 'text-muted')
    accent = get_color(css_vars, 'accent', 'green-400', 'green-500', 'blue',
                       'primary', 'neon', 'mint')

    layers = []

    # Card background
    layers.append(make_rectangle("Card BG", 0, 0, w, h, fill_color=surface,
                                 border_color=border, corner_radius=radius))

    # Image placeholder
    placeholder_col = hex_to_sketch_color("#cccccc", 0.2)
    layers.append(make_rectangle("Image", 1, 1, w - 2, img_h,
                                 fill_color=placeholder_col, corner_radius=0))
    layers.append(make_text("📷", "📷 Image", w // 2 - 30, img_h // 2 - 10,
                            60, 20, font_size=12, font_name="Inter-Medium",
                            color=muted, alignment=2))

    cy = img_h + 16
    layers.append(make_text("Title", card['title'], 16, cy, w - 32, 22,
                            font_size=15, font_name="Inter-SemiBold",
                            color=text_col))
    cy += 28
    layers.append(make_text("Meta", card['meta'], 16, cy, w - 32, 18,
                            font_size=12, font_name="Inter-Regular", color=muted))
    cy += 24
    layers.append(make_text("Ingredients", card['ingredients'], 16, cy,
                            w - 32, 36, font_size=12, font_name="Inter-Regular",
                            color=muted, line_height=18))

    # Footer
    layers.append(make_text("CO₂", card['co2'], 16, h - 30, w // 2, 18,
                            font_size=12, font_name="Inter-Regular", color=muted))
    layers.append(make_text("Swaps", card['swaps'], w // 2, h - 30,
                            w // 2 - 16, 18, font_size=12,
                            font_name="Inter-SemiBold", color=accent,
                            alignment=2))

    return make_group(f"Card: {card['title']}", x, y, w, h, layers)


def build_recipe_grid(css_vars, cards, y, cols=3, content_x=CONTENT_X,
                      content_w=CONTENT_MAX_W, radius=12):
    """Build the recipe card grid. Returns (group, next_y)."""
    gap = 20
    card_w = (content_w - gap * (cols - 1)) // cols
    card_h = 340
    img_h = 180

    layers = []
    row = col = 0
    for card in cards:
        cx = col * (card_w + gap)
        cy = row * (card_h + gap)
        layers.append(build_recipe_card(css_vars, card, cx, cy, card_w,
                                        card_h, img_h, radius))
        col += 1
        if col >= cols:
            col = 0
            row += 1

    total_rows = (len(cards) + cols - 1) // cols
    grid_h = total_rows * (card_h + gap) - gap

    return (make_group("Recipe Grid", content_x, y, content_w, grid_h, layers),
            y + grid_h + 32)


def build_analyze_form(css_vars, y, content_x=CONTENT_X,
                       content_w=CONTENT_MAX_W, is_hero=False, radius=12):
    """Build the analyze / custom recipe form. Returns (group, next_y)."""
    surface = get_color(css_vars, 'surface', 'surface-1')
    surface2 = get_color(css_vars, 'surface-2', 'bg')
    border = get_color(css_vars, 'border')
    text_col = get_color(css_vars, 'text')
    muted = get_color(css_vars, 'text-muted')
    accent = get_color(css_vars, 'accent', 'green-400', 'green-600', 'blue',
                       'primary', 'neon')
    accent_dark = get_color(css_vars, 'accent-dark', 'green-600', 'green-700',
                            'blue-dark', 'neon-dark', 'primary')

    form_h = 340
    layers = []

    # Background
    bdr = accent if is_hero else border
    layers.append(make_rectangle("Form BG", 0, 0, content_w, form_h,
                                 fill_color=surface, border_color=bdr,
                                 border_width=2 if is_hero else 1,
                                 corner_radius=radius))

    fy = 24
    title = "🔬 Analyze Your Recipe" if is_hero else "📝 Add Your Own Recipe"
    layers.append(make_text("Form Title", title, 24, fy, content_w - 48, 28,
                            font_size=18,
                            font_name="PlayfairDisplay-SemiBold" if is_hero
                            else "Inter-SemiBold",
                            color=accent if is_hero else text_col))
    fy += 36

    if is_hero:
        layers.append(make_text(
            "Form Desc",
            "Paste your ingredients and we'll show the environmental impact "
            "+ greener alternatives.",
            24, fy, content_w - 48, 20, font_size=14,
            font_name="Inter-Regular", color=muted))
        fy += 32

    # Recipe Name
    layers.append(make_text("Label: Name", "Recipe Name", 24, fy, 200, 16,
                            font_size=13, font_name="Inter-SemiBold",
                            color=muted))
    fy += 22
    layers.append(make_rectangle("Input: Name", 24, fy, content_w - 48, 40,
                                 fill_color=surface2, border_color=border,
                                 corner_radius=8))
    layers.append(make_text("Placeholder", "e.g., Spaghetti Carbonara",
                            36, fy + 10, 300, 20, font_size=14,
                            font_name="Inter-Regular", color=muted))
    fy += 52

    # Ingredients
    layers.append(make_text("Label: Ingredients",
                            "Ingredients (one per line: amount unit ingredient)",
                            24, fy, 400, 16, font_size=13,
                            font_name="Inter-SemiBold", color=muted))
    fy += 22
    layers.append(make_rectangle("Input: Ingredients", 24, fy,
                                 content_w - 48, 80, fill_color=surface2,
                                 border_color=border, corner_radius=8))
    layers.append(make_text("Placeholder", "500g beef\n400g tomatoes\n200g pasta",
                            36, fy + 10, 300, 60, font_size=14,
                            font_name="Inter-Regular", color=muted))
    fy += 92

    # Button
    btn_w = 180
    layers.append(make_rectangle("Button BG", 24, fy, btn_w, 42,
                                 fill_color=accent_dark, corner_radius=8))
    layers.append(make_text("Button", "🔍 Analyze Recipe", 24, fy + 11,
                            btn_w, 20, font_size=14,
                            font_name="Inter-SemiBold",
                            color=hex_to_sketch_color("#ffffff"),
                            alignment=2))

    return (make_group("Analyze Form", content_x, y, content_w, form_h, layers),
            y + form_h + 32)


def build_section_divider(css_vars, text, y, content_x=CONTENT_X,
                          content_w=CONTENT_MAX_W):
    """Build a decorative divider with centered text. Returns (group, next_y)."""
    border = get_color(css_vars, 'border')
    muted = get_color(css_vars, 'text-muted')
    text_w = len(text) * 7 + 16
    line_w = (content_w - text_w - 32) // 2

    layers = [
        make_rectangle("Line L", 0, 10, line_w, 1, fill_color=border),
        make_text("Divider Text", text, line_w + 16, 2, text_w, 20,
                  font_size=13, font_name="Inter-Medium", color=muted,
                  alignment=2),
        make_rectangle("Line R", line_w + text_w + 32, 10, line_w, 1,
                       fill_color=border),
    ]
    return (make_group("Divider", content_x, y, content_w, 24, layers),
            y + 48)


def build_impact_dashboard(css_vars, y, content_x=CONTENT_X,
                           content_w=CONTENT_MAX_W, radius=14):
    """Build the eco-impact stats banner. Returns (group, next_y)."""
    accent_dark = get_color(css_vars, 'accent-dark', 'blue-dark', 'green-600',
                            'purple-dark', 'teal-dark', 'accent')
    white = hex_to_sketch_color("#ffffff")
    white70 = hex_to_sketch_color("#ffffff", 0.7)

    dash_h = 160
    layers = [
        make_rectangle("Dashboard BG", 0, 0, content_w, dash_h,
                       fill_color=accent_dark, corner_radius=radius),
        make_text("Title", "📊 Your Eco Impact", 32, 20, 300, 28,
                  font_size=20, font_name="PlayfairDisplay-Bold", color=white),
    ]

    stats = [
        ("12.4 kg", "CO₂ Saved"), ("23", "Meals Optimized"),
        ("15", "Swaps Made"), ("3", "Day Streak"),
    ]
    stat_w = (content_w - 64) // 4
    for i, (val, label) in enumerate(stats):
        sx = 32 + i * stat_w
        layers.append(make_text(f"Stat: {label}", val, sx, 64, stat_w - 16, 32,
                                font_size=24, font_name="Inter-Bold",
                                color=white))
        layers.append(make_text(f"Label: {label}", label, sx, 100,
                                stat_w - 16, 18, font_size=12,
                                font_name="Inter-Regular", color=white70))

    return (make_group("Impact Dashboard", content_x, y, content_w, dash_h,
                       layers),
            y + dash_h + 32)


def build_chat_section(css_vars, y, content_x=CONTENT_X,
                       content_w=CONTENT_MAX_W, radius=14):
    """Build the AI chat section. Returns (group, next_y)."""
    surface = get_color(css_vars, 'surface', 'surface-1')
    surface2 = get_color(css_vars, 'surface-2')
    border = get_color(css_vars, 'border')
    text_col = get_color(css_vars, 'text')
    muted = get_color(css_vars, 'text-muted')
    accent = get_color(css_vars, 'accent', 'green-400', 'green')
    white = hex_to_sketch_color("#ffffff")

    chat_h = 420
    layers = []

    layers.append(make_rectangle("Chat BG", 0, 0, content_w, chat_h,
                                 fill_color=surface, border_color=border,
                                 corner_radius=radius))

    # Header
    layers.append(make_text("Avatar", "🤖", 24, 20, 28, 28, font_size=20,
                            font_name="Inter-Regular", color=accent))
    layers.append(make_text("AI Name", "Eco-Nudge AI", 56, 22, 200, 24,
                            font_size=16, font_name="Inter-SemiBold",
                            color=text_col))
    layers.append(make_text("Status", "Online • Ready to help", 56, 44, 200,
                            16, font_size=12, font_name="Inter-Regular",
                            color=accent))
    layers.append(make_rectangle("Divider", 0, 70, content_w, 1,
                                 fill_color=border))

    # AI bubble
    layers.append(make_rectangle("Bubble BG", 24, 86, content_w - 120, 140,
                                 fill_color=surface2, corner_radius=12))
    layers.append(make_text(
        "AI Message",
        ("Hi! I'm your eco-cooking assistant. I can help you:\n"
         "• Find greener ingredient swaps\n"
         "• Estimate carbon footprints\n"
         "• Suggest seasonal recipes\n"
         "• Track your environmental impact"),
        40, 100, content_w - 160, 116, font_size=14,
        font_name="Inter-Regular", color=text_col, line_height=22))

    # Quick prompts
    prompts = ["Suggest a low-carbon dinner", "What's in season now?",
               "Make my recipe greener"]
    px = 24
    for prompt in prompts:
        pw = len(prompt) * 7 + 24
        layers.append(make_rectangle(
            f"Prompt: {prompt[:20]}", px, 244, pw, 32,
            fill_color=with_alpha(accent, 0.1), border_color=accent,
            corner_radius=16))
        layers.append(make_text(
            f"Prompt Text", prompt, px + 12, 251, pw - 24, 18,
            font_size=13, font_name="Inter-Medium", color=accent))
        px += pw + 12

    # Input bar
    layers.append(make_rectangle("Input BG", 24, chat_h - 64,
                                 content_w - 48, 44, fill_color=surface2,
                                 border_color=border, corner_radius=22))
    layers.append(make_text("Input Placeholder",
                            "Ask me about eco-friendly cooking...",
                            44, chat_h - 52, content_w - 140, 20, font_size=14,
                            font_name="Inter-Regular", color=muted))
    layers.append(make_rectangle("Send Btn", content_w - 84, chat_h - 58,
                                 36, 36, fill_color=accent, corner_radius=18))
    layers.append(make_text("Send", "↑", content_w - 76, chat_h - 52, 20, 20,
                            font_size=16, font_name="Inter-Bold", color=white,
                            alignment=2))

    return (make_group("Chat Section", content_x, y, content_w, chat_h,
                       layers),
            y + chat_h + 32)


def build_filter_pills(css_vars, y, filters, content_x=CONTENT_X,
                       content_w=CONTENT_MAX_W):
    """Build a row of filter pill buttons. Returns (group, next_y)."""
    accent = get_color(css_vars, 'accent', 'neon', 'primary')
    muted = get_color(css_vars, 'text-muted')
    border = get_color(css_vars, 'border')

    layers = []
    px = 0
    for i, label in enumerate(filters):
        pw = len(label) * 8 + 24
        is_active = (i == 0)
        if is_active:
            layers.append(make_rectangle(
                f"Pill: {label}", px, 0, pw, 36, fill_color=accent,
                corner_radius=18))
            layers.append(make_text(
                label, label, px + 12, 8, pw - 24, 20, font_size=13,
                font_name="Inter-SemiBold",
                color=hex_to_sketch_color("#000000")))
        else:
            layers.append(make_rectangle(
                f"Pill: {label}", px, 0, pw, 36,
                border_color=border, corner_radius=18))
            layers.append(make_text(
                label, label, px + 12, 8, pw - 24, 20, font_size=13,
                font_name="Inter-Medium", color=muted))
        px += pw + 12

    return (make_group("Filter Pills", content_x, y, content_w, 36, layers),
            y + 60)


def build_compact_recipe_list(css_vars, cards, y, content_x=CONTENT_X,
                              content_w=CONTENT_MAX_W, radius=14):
    """Build a compact row-based recipe list. Returns (group, next_y)."""
    surface = get_color(css_vars, 'surface', 'surface-1')
    border = get_color(css_vars, 'border')
    text_col = get_color(css_vars, 'text')
    muted = get_color(css_vars, 'text-muted')
    accent = get_color(css_vars, 'accent', 'green-400')

    row_h = 64
    gap = 8
    total_h = len(cards) * (row_h + gap) + 48
    layers = []

    layers.append(make_rectangle("List BG", 0, 0, content_w, total_h,
                                 fill_color=surface, border_color=border,
                                 corner_radius=radius))
    layers.append(make_text("List Title", "📋 Suggested Recipes", 20, 16,
                            300, 24, font_size=16, font_name="Inter-SemiBold",
                            color=text_col))

    ry = 48
    for card in cards:
        # Thumbnail
        layers.append(make_rectangle(
            "Thumb", 16, ry + 7, 50, 50,
            fill_color=hex_to_sketch_color("#cccccc", 0.2), corner_radius=8))
        layers.append(make_text(
            f"Row: {card['title']}", card['title'], 80, ry + 10,
            content_w - 220, 20, font_size=14, font_name="Inter-Medium",
            color=text_col))
        layers.append(make_text(
            f"Meta", card['meta'][:35], 80, ry + 32, content_w - 220, 16,
            font_size=12, font_name="Inter-Regular", color=muted))
        layers.append(make_text(
            f"CO₂", card['co2'], content_w - 180, ry + 20, 160, 20,
            font_size=12, font_name="Inter-Medium", color=accent,
            alignment=2))
        layers.append(make_rectangle(
            "Divider", 16, ry + row_h, content_w - 32, 1,
            fill_color=border))
        ry += row_h + gap

    return (make_group("Compact Recipe List", content_x, y, content_w,
                       total_h, layers),
            y + total_h + 32)


def build_eco_tip_card(css_vars, y, content_x=CONTENT_X,
                       content_w=CONTENT_MAX_W, radius=14):
    """Build an eco tip card. Returns (group, next_y)."""
    surface2 = get_color(css_vars, 'surface-2', 'surface')
    border = get_color(css_vars, 'border')
    accent = get_color(css_vars, 'primary', 'accent', 'mint', 'green')
    text_col = get_color(css_vars, 'text')
    muted = get_color(css_vars, 'text-muted')

    tip_h = 140
    layers = [
        make_rectangle("Tip BG", 0, 0, content_w, tip_h,
                       fill_color=surface2, border_color=border,
                       corner_radius=radius),
        make_text("💡", "💡", 20, 20, 28, 28, font_size=20,
                  font_name="Inter-Regular", color=accent),
        make_text("Tip Title", "Eco Tip of the Day", 20, 52,
                  content_w - 40, 20, font_size=15,
                  font_name="Inter-SemiBold", color=text_col),
        make_text("Tip Text",
                  "Seasonal vegetables have up to 50% lower carbon footprint "
                  "than out-of-season imports.",
                  20, 78, content_w - 40, 40, font_size=13,
                  font_name="Inter-Regular", color=muted, line_height=20),
    ]

    return (make_group("Eco Tip", content_x, y, content_w, tip_h, layers),
            y + tip_h + 24)


# ============================================================
# SECTION 6: Design Tokens Artboard
# ============================================================

def build_design_tokens_artboard(css_vars, sketch_name):
    """Build a design-tokens artboard showing colors, typography, spacing."""
    layers = []
    y = 40
    black = hex_to_sketch_color("#333333")
    gray = hex_to_sketch_color("#999999")
    dgray = hex_to_sketch_color("#666666")

    layers.append(make_text("Title", f"Design Tokens — {sketch_name}",
                            40, y, 900, 36, font_size=24,
                            font_name="Inter-Bold", color=black))
    y += 60

    # ---- Color Palette ----
    layers.append(make_text("Section", "COLOR PALETTE", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32
    swatch_size = 56
    col = 0
    max_cols = 6
    col_w = swatch_size + 120

    for var_name, var_value in css_vars.items():
        if not (var_value.startswith('#') or var_value.startswith('rgb')):
            continue
        sx = 40 + col * col_w
        color = parse_css_color(var_value)
        layers.append(make_rectangle(
            f"Swatch: {var_name}", sx, y, swatch_size, swatch_size,
            fill_color=color, border_color=hex_to_sketch_color("#dddddd"),
            corner_radius=8))
        layers.append(make_text(
            f"Name: {var_name}", f"--{var_name}", sx, y + swatch_size + 4,
            col_w, 14, font_size=10, font_name="Inter-Medium", color=dgray))
        layers.append(make_text(
            f"Val: {var_name}", var_value, sx, y + swatch_size + 18,
            col_w, 12, font_size=9, font_name="Inter-Regular", color=gray))
        col += 1
        if col >= max_cols:
            col = 0
            y += swatch_size + 48

    y += swatch_size + 64

    # ---- Typography ----
    layers.append(make_text("Section", "TYPOGRAPHY", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32
    specimens = [
        ("Display / H1", "PlayfairDisplay-Bold", 28),
        ("Display / H2", "PlayfairDisplay-SemiBold", 20),
        ("Body / Regular", "Inter-Regular", 14),
        ("Body / Medium", "Inter-Medium", 14),
        ("Body / SemiBold", "Inter-SemiBold", 14),
        ("Caption", "Inter-Regular", 12),
        ("Button", "Inter-SemiBold", 14),
    ]
    for label, font, size in specimens:
        h = int(size * 1.6)
        layers.append(make_text(
            f"Type: {label}", f"{label}  —  {font} @ {size}px",
            40, y, 700, h, font_size=size, font_name=font, color=black))
        y += h + 12

    y += 40

    # ---- Spacing / Radius ----
    layers.append(make_text("Section", "SPACING & RADIUS", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32
    radius_val = css_vars.get('radius', '12px')
    layers.append(make_text("Radius", f"Border Radius: {radius_val}",
                            40, y, 300, 20, font_size=14,
                            font_name="Inter-Regular", color=black))
    y += 60

    return make_artboard("Design Tokens", 1440, max(y, 600),
                         bg_color=hex_to_sketch_color("#ffffff"),
                         layers=layers)


# ============================================================
# SECTION 7: Standard Recipe Data
# ============================================================

RECIPES = [
    {
        "title": "Classic Beef Bolognese",
        "meta": "🍽️ 4 servings  ·  ⏱️ 45 min  ·  🌍 Italian",
        "ingredients": "beef, tomatoes, onions, garlic, olive oil, pasta, cheese",
        "co2": "🌿 4.02 kg CO₂e/serving",
        "swaps": "2 swaps available"
    },
    {
        "title": "Chicken Stir-Fry",
        "meta": "🍽️ 3 servings  ·  ⏱️ 25 min  ·  🌍 Asian",
        "ingredients": "chicken, rice, broccoli, peppers, soy sauce",
        "co2": "🌿 1.35 kg CO₂e/serving",
        "swaps": "2 swaps available"
    },
    {
        "title": "Lamb Curry",
        "meta": "🍽️ 4 servings  ·  ⏱️ 60 min  ·  🌍 Indian",
        "ingredients": "lamb, onions, tomatoes, garlic, ginger, cream, rice",
        "co2": "🌿 3.72 kg CO₂e/serving",
        "swaps": "3 swaps available"
    },
    {
        "title": "Salmon with Buttered Vegetables",
        "meta": "🍽️ 2 servings  ·  ⏱️ 35 min  ·  🌍 European",
        "ingredients": "salmon, butter, potatoes, broccoli, lemon",
        "co2": "🌿 2.01 kg CO₂e/serving",
        "swaps": "2 swaps available"
    },
    {
        "title": "Bacon Cheeseburger",
        "meta": "🍽️ 4 servings  ·  ⏱️ 20 min  ·  🌍 American",
        "ingredients": "beef, bacon, cheese, bread, lettuce",
        "co2": "🌿 4.34 kg CO₂e/serving",
        "swaps": "3 swaps available"
    },
    {
        "title": "Vegetable Lentil Soup",
        "meta": "🍽️ 4 servings  ·  ⏱️ 40 min  ·  🌍 Mediterranean",
        "ingredients": "lentils, carrots, onions, celery, tomatoes, spinach",
        "co2": "🌿 0.21 kg CO₂e/serving",
        "swaps": "Already eco-friendly!"
    },
]

NAV_ITEMS = ["Meal Planner", "AI Assistant", "My Recipes", "My Impact",
             "Settings"]


# ============================================================
# SECTION 8: Per-Sketch Layout Functions
# ============================================================

def layout_01(v, r):
    """Sketch 01 — Dark, original order: grid → form."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS)
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Meal Planner",
                          "Browse recipes or add your own. We'll help you make "
                          "eco-friendly choices.", y)
    layers.append(hdr)
    grid, y = build_recipe_grid(v, r, y, cols=3, radius=rad)
    layers.append(grid)
    form, y = build_analyze_form(v, y, radius=rad)
    layers.append(form)
    return layers, y + 40


def layout_02(v, r):
    """Sketch 02 — Dark, recipe input first."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS)
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Meal Planner",
                          "Paste your recipe for instant eco-analysis, or browse "
                          "suggestions below.", y)
    layers.append(hdr)
    form, y = build_analyze_form(v, y, is_hero=True, radius=rad)
    layers.append(form)
    div, y = build_section_divider(v, "or browse suggested recipes", y)
    layers.append(div)
    grid, y = build_recipe_grid(v, r, y, cols=3, radius=rad)
    layers.append(grid)
    return layers, y + 40


def layout_03(v, r):
    """Sketch 03 — Light warm earth tones, centered, featured card."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS, brand_icon="🌾")
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Meal Planner",
                          "Browse recipes or add your own. We'll help you make "
                          "eco-friendly choices.", y, centered=True)
    layers.append(hdr)
    grid, y = build_recipe_grid(v, r, y, cols=3, radius=rad)
    layers.append(grid)
    form, y = build_analyze_form(v, y, radius=rad)
    layers.append(form)
    return layers, y + 40


def layout_04(v, r):
    """Sketch 04 — Light, sidebar navigation."""
    rad = get_radius(v)
    layers = []
    sidebar, sw = build_sidebar_nav(v, NAV_ITEMS)
    layers.append(sidebar)
    cx = sw + 32
    cw = ARTBOARD_W - sw - 64
    y = 32
    hdr, y = build_header(v, "Meal Planner",
                          "Analyze your recipes or browse eco-friendly "
                          "suggestions.", y, content_x=cx)
    layers.append(hdr)
    form, y = build_analyze_form(v, y, content_x=cx, content_w=cw,
                                 is_hero=True, radius=rad)
    layers.append(form)
    div, y = build_section_divider(v, "Suggested Recipes", y,
                                   content_x=cx, content_w=cw)
    layers.append(div)
    grid, y = build_recipe_grid(v, r, y, cols=3, content_x=cx,
                                content_w=cw, radius=rad)
    layers.append(grid)
    return layers, max(y + 40, 1024)


def layout_05(v, r):
    """Sketch 05 — Dark purple + teal, stats panel."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS[:4])
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Eco Meal Planner",
                          "Your sustainable cooking dashboard", y)
    layers.append(hdr)
    half_w = (CONTENT_MAX_W - 24) // 2
    dash, _ = build_impact_dashboard(v, y, content_w=half_w)
    layers.append(dash)
    form, _ = build_analyze_form(v, y,
                                 content_x=CONTENT_X + half_w + 24,
                                 content_w=half_w, is_hero=True, radius=rad)
    layers.append(form)
    y += 350
    grid, y = build_recipe_grid(v, r, y, cols=3, radius=rad)
    layers.append(grid)
    return layers, y + 40


def layout_06(v, r):
    """Sketch 06 — Light blue, impact dashboard first."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS[:4])
    layers.append(nav)
    y += 32
    dash, y = build_impact_dashboard(v, y)
    layers.append(dash)
    fw = 340
    gw = CONTENT_MAX_W - fw - 24
    form, yf = build_analyze_form(v, y, content_w=fw, is_hero=True,
                                  radius=rad)
    layers.append(form)
    grid, yg = build_recipe_grid(v, r, y, cols=2,
                                 content_x=CONTENT_X + fw + 24,
                                 content_w=gw, radius=rad)
    layers.append(grid)
    return layers, max(yf, yg) + 40


def layout_07(v, r):
    """Sketch 07 — Dark, chat-first layout."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS)
    layers.append(nav)
    y += 32
    chat, y = build_chat_section(v, y, radius=rad)
    layers.append(chat)
    half_w = (CONTENT_MAX_W - 24) // 2
    form, yf = build_analyze_form(v, y, content_w=half_w, radius=rad)
    layers.append(form)
    rlist, yr = build_compact_recipe_list(
        v, r, y, content_x=CONTENT_X + half_w + 24,
        content_w=half_w, radius=rad)
    layers.append(rlist)
    return layers, max(yf, yr) + 40


def layout_08(v, r):
    """Sketch 08 — Light minimalist, large cards."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS[:4])
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Plan Better Meals",
                          "Discover the environmental impact of your recipes and "
                          "find greener alternatives.", y, centered=True)
    layers.append(hdr)
    fw = 700
    fx = (ARTBOARD_W - fw) // 2
    form, y = build_analyze_form(v, y, content_x=fx, content_w=fw,
                                 is_hero=True, radius=rad)
    layers.append(form)
    grid, y = build_recipe_grid(v, r, y, cols=2, radius=rad)
    layers.append(grid)
    return layers, y + 40


def layout_09(v, r):
    """Sketch 09 — Dark neon, centered hero + filter pills."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS[:4])
    layers.append(nav)
    y += 32
    hdr, y = build_header(v, "Cook Greener, Eat Better",
                          "Analyze your recipes' environmental footprint "
                          "instantly.", y, centered=True)
    layers.append(hdr)
    fw = 650
    fx = (ARTBOARD_W - fw) // 2
    form, y = build_analyze_form(v, y, content_x=fx, content_w=fw,
                                 is_hero=True, radius=rad)
    layers.append(form)
    pills, y = build_filter_pills(v, y,
                                  ["All", "Low CO₂", "High Protein", "Quick"])
    layers.append(pills)
    grid, y = build_recipe_grid(v, r, y, cols=3, radius=rad)
    layers.append(grid)
    return layers, y + 40


def layout_10(v, r):
    """Sketch 10 — Light pastel, persistent two-column layout."""
    rad = get_radius(v)
    layers = []
    nav, y = build_top_nav(v, NAV_ITEMS[:4])
    layers.append(nav)
    y += 32
    lw = 340
    rw = CONTENT_MAX_W - lw - 24
    rx = CONTENT_X + lw + 24
    form, yf = build_analyze_form(v, y, content_w=lw, is_hero=True,
                                  radius=rad)
    layers.append(form)
    tip, yt = build_eco_tip_card(v, yf, content_w=lw, radius=rad)
    layers.append(tip)
    pills, yr = build_filter_pills(v, y, ["All", "Low CO₂", "Quick",
                                          "Vegetarian"],
                                   content_x=rx, content_w=rw)
    layers.append(pills)
    grid, yr = build_recipe_grid(v, r, yr, cols=2, content_x=rx,
                                 content_w=rw, radius=rad)
    layers.append(grid)
    return layers, max(yt, yr) + 40


LAYOUT_MAP = {
    'sketch-01': layout_01,
    'sketch-02': layout_02,
    'sketch-03': layout_03,
    'sketch-04': layout_04,
    'sketch-05': layout_05,
    'sketch-06': layout_06,
    'sketch-07': layout_07,
    'sketch-08': layout_08,
    'sketch-09': layout_09,
    'sketch-10': layout_10,
}


# ============================================================
# SECTION 9: File Assembly & Main
# ============================================================

def process_sketch_file(html_path, output_dir):
    """Convert one HTML sketch to a .sketch file."""
    filename = os.path.basename(html_path)
    parts = filename.replace('.html', '').split('-')
    sketch_key = parts[0] + '-' + parts[1] if len(parts) >= 2 else 'sketch-01'
    sketch_name = os.path.splitext(filename)[0]

    print(f"  Processing: {filename}")

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    css_vars = extract_css_vars(html)
    bg_color = get_color(css_vars, 'bg')

    layout_fn = LAYOUT_MAP.get(sketch_key, layout_01)
    artboard_layers, artboard_h = layout_fn(css_vars, RECIPES)

    # Main artboard
    main_ab = make_artboard(sketch_name, ARTBOARD_W, int(artboard_h),
                            bg_color, artboard_layers)

    # Design tokens artboard (placed to the right)
    tokens_ab = build_design_tokens_artboard(css_vars, sketch_name)
    tokens_ab["frame"]["x"] = ARTBOARD_W + 100

    page = make_page("Page 1", [main_ab, tokens_ab])
    document = make_document([page])
    meta = make_meta([page])
    user = make_user([page])

    output_path = os.path.join(output_dir, f"{sketch_name}.sketch")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('document.json', json.dumps(document, indent=2))
        zf.writestr('meta.json', json.dumps(meta, indent=2))
        zf.writestr('user.json', json.dumps(user, indent=2))
        zf.writestr(f'pages/{page["do_objectID"]}.json',
                    json.dumps(page, indent=2))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"    -> {output_path}  ({size_kb:.1f} KB)")
    return output_path


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sketches_dir = os.path.join(script_dir, 'sketches')
    output_dir = os.path.join(script_dir, 'output-sketch')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 62)
    print("  HTML Sketch -> Sketch (.sketch) File Converter")
    print("=" * 62)
    print(f"  Input:  {sketches_dir}")
    print(f"  Output: {output_dir}")
    print()

    html_files = sorted(
        f for f in os.listdir(sketches_dir) if f.endswith('.html'))

    if not html_files:
        print("  No HTML files found in sketches/ directory.")
        sys.exit(1)

    print(f"  Found {len(html_files)} sketch file(s) to convert.\n")

    results = []
    for html_file in html_files:
        html_path = os.path.join(sketches_dir, html_file)
        try:
            result = process_sketch_file(html_path, output_dir)
            results.append(result)
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 62}")
    print(f"  Done! Created {len(results)} .sketch file(s).")
    print()
    print("  These files can be:")
    print("    * Opened in Sketch (macOS)")
    print("    * Imported into Figma  (File > Import Sketch file)")
    print("    * Imported into Penpot (Sketch importer)")
    print("    * Opened in Lunacy    (free, Windows/Mac/Linux)")
    print(f"{'=' * 62}")


if __name__ == '__main__':
    main()
