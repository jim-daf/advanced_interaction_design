#!/usr/bin/env python3
"""
AI Assistant View — Sketch (.sketch) File Generator
=====================================================
Generates 4 different AI Assistant view sketches (2 dark, 2 light)
based on the chat view from index.html / styles.css.

Usage:
    python generate-ai-sketches.py
"""

import os
import sys
import json
import uuid
import zipfile

# ============================================================
# CORE SKETCH FACTORIES (same as convert-to-sketch.py)
# ============================================================

def new_uuid():
    return str(uuid.uuid4()).upper()

def hex_to_sketch_color(hex_str, alpha=1.0):
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    if len(hex_str) < 6:
        hex_str = hex_str.ljust(6, '0')
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"_class": "color", "alpha": alpha, "blue": b, "green": g, "red": r}

def with_alpha(color, alpha):
    return {**color, "alpha": alpha}

def make_rect(x, y, w, h):
    return {"_class": "rect", "constrainProportions": False,
            "height": float(h), "width": float(w), "x": float(x), "y": float(y)}

def make_export_options():
    return {"_class": "exportOptions", "includedLayerIds": [],
            "layerOptions": 0, "shouldTrim": False, "exportFormats": []}

def make_base_layer(cls, name, x, y, w, h):
    return {
        "_class": cls, "do_objectID": new_uuid(), "booleanOperation": -1,
        "isFixedToViewport": False, "isFlippedHorizontal": False,
        "isFlippedVertical": False, "isLocked": False, "isVisible": True,
        "layerListExpandedType": 0, "name": name, "nameIsFixed": True,
        "resizingConstraint": 63, "resizingType": 0, "rotation": 0,
        "shouldBreakMaskChain": False, "exportOptions": make_export_options(),
        "frame": make_rect(x, y, w, h), "clippingMaskMode": 0,
        "hasClippingMask": False,
    }

def make_style(fills=None, borders=None, shadows=None):
    return {"_class": "style", "endMarkerType": 0, "miterLimit": 10,
            "startMarkerType": 0, "windingRule": 1,
            "fills": fills or [], "borders": borders or [],
            "shadows": shadows or [], "innerShadows": []}

def make_fill(color, fill_type=0):
    return {"_class": "fill", "isEnabled": True, "fillType": fill_type,
            "color": color}

def make_border(color, thickness=1, position=1):
    return {"_class": "border", "isEnabled": True, "fillType": 0,
            "color": color, "thickness": float(thickness), "position": position}

def make_shadow(color, x=0, y=4, blur=24, spread=0):
    return {"_class": "shadow", "isEnabled": True, "blurRadius": float(blur),
            "color": color,
            "contextSettings": {"_class": "graphicsContextSettings",
                                "blendMode": 0, "opacity": 1},
            "offsetX": float(x), "offsetY": float(y), "spread": float(spread)}

def make_rectangle(name, x, y, w, h, fill_color=None, border_color=None,
                   border_width=1, corner_radius=0, shadows=None):
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
            "_class": "paragraphStyle", "alignment": alignment,
            "maximumLineHeight": float(line_height),
            "minimumLineHeight": float(line_height)
        },
        "kerning": 0
    }
    layer["style"] = make_style()
    layer["style"]["textStyle"] = {
        "_class": "textStyle", "verticalAlignment": 0,
        "encodedAttributes": encoded_attrs
    }
    layer["automaticallyDrawOnUnderlyingPath"] = False
    layer["dontSynchroniseWithSymbol"] = False
    layer["lineSpacingBehaviour"] = 2
    layer["textBehaviour"] = 1
    layer["glyphBounds"] = "{{0, 3}, {%d, %d}}" % (int(w), int(h))
    layer["attributedString"] = {
        "_class": "attributedString", "string": string,
        "attributes": [{"_class": "stringAttribute", "location": 0,
                         "length": len(string), "attributes": encoded_attrs}]
    }
    return layer

def make_group(name, x, y, w, h, layers=None):
    layer = make_base_layer("group", name, x, y, w, h)
    layer["style"] = make_style()
    layer["layers"] = layers or []
    return layer

def make_artboard(name, w, h, bg_color=None, layers=None):
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
    page = make_base_layer("page", name, 0, 0, 0, 0)
    page["style"] = make_style()
    page["layers"] = artboards or []
    for key in ["clippingMaskMode", "hasClippingMask", "booleanOperation"]:
        page.pop(key, None)
    return page

def make_document(pages):
    return {
        "_class": "document", "do_objectID": new_uuid(), "colorSpace": 1,
        "currentPageIndex": 0, "foreignLayerStyles": [],
        "foreignSymbols": [], "foreignTextStyles": [],
        "layerStyles": {"_class": "sharedStyleContainer", "objects": []},
        "layerTextStyles": {"_class": "sharedTextStyleContainer", "objects": []},
        "pages": [{"_class": "MSJSONFileReference", "_ref_class": "MSImmutablePage",
                    "_ref": "pages/" + p["do_objectID"]} for p in pages]
    }

def make_meta(pages):
    paa = {}
    for p in pages:
        ab_dict = {}
        for l in p.get("layers", []):
            if l["_class"] == "artboard":
                ab_dict[l["do_objectID"]] = {"name": l["name"]}
        paa[p["do_objectID"]] = {"name": p["name"], "artboards": ab_dict}
    return {
        "commit": "generated-by-converter", "pagesAndArtboards": paa,
        "version": 136, "compatibilityVersion": 99,
        "app": "com.bohemiancoding.sketch3", "autosaved": 0,
        "variant": "NONAPPSTORE",
        "created": {"commit": "generated-by-converter", "appVersion": "96",
                     "build": 0, "app": "com.bohemiancoding.sketch3",
                     "compatibilityVersion": 99, "version": 136,
                     "variant": "NONAPPSTORE"},
        "saveHistory": ["NONAPPSTORE.96"], "appVersion": "96", "build": 0
    }

def make_user(pages):
    user = {"document": {"pageListHeight": 110, "pageListCollapsed": 0}}
    for p in pages:
        user[p["do_objectID"]] = {"scrollOrigin": "{0, 0}", "zoomValue": 1}
    return user

def write_sketch_file(output_path, page):
    document = make_document([page])
    meta = make_meta([page])
    user = make_user([page])
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('document.json', json.dumps(document, indent=2))
        zf.writestr('meta.json', json.dumps(meta, indent=2))
        zf.writestr('user.json', json.dumps(user, indent=2))
        zf.writestr(f'pages/{page["do_objectID"]}.json',
                    json.dumps(page, indent=2))
    size_kb = os.path.getsize(output_path) / 1024
    print(f"    -> {output_path}  ({size_kb:.1f} KB)")


# ============================================================
# THEME DEFINITIONS
# ============================================================

THEME_DARK_GREEN = {
    "name": "Dark Green",
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "surface2": "#242836",
    "surface3": "#2c3040",
    "border": "#2e3348",
    "text": "#e4e6f0",
    "text_muted": "#8b8fa8",
    "accent": "#4ade80",
    "accent_dark": "#16a34a",
    "accent_dim": "#22c55e",
    "accent_bg": "#16a34a1f",
    "user_bubble": "#16a34a",
    "user_text": "#ffffff",
    "ai_bubble": "#242836",
    "ai_text": "#e4e6f0",
    "input_bg": "#242836",
    "card_shadow": "#00000066",
}

THEME_DARK_PURPLE = {
    "name": "Dark Purple-Teal",
    "bg": "#0d0b14",
    "surface": "#16131f",
    "surface2": "#1e1a2a",
    "surface3": "#262240",
    "border": "#2d2840",
    "text": "#e3dfef",
    "text_muted": "#8b85a3",
    "accent": "#a78bfa",
    "accent_dark": "#7c3aed",
    "accent_dim": "#b49ef5",
    "accent_bg": "#a78bfa1a",
    "user_bubble": "#7c3aed",
    "user_text": "#ffffff",
    "ai_bubble": "#1e1a2a",
    "ai_text": "#e3dfef",
    "input_bg": "#1e1a2a",
    "teal": "#2dd4bf",
    "teal_bg": "#2dd4bf1a",
    "card_shadow": "#00000066",
}

THEME_LIGHT_GREEN = {
    "name": "Light Green",
    "bg": "#f9fafb",
    "surface": "#ffffff",
    "surface2": "#f3f4f6",
    "surface3": "#e5e7eb",
    "border": "#e2e8f0",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "accent": "#22c55e",
    "accent_dark": "#16a34a",
    "accent_dim": "#4ade80",
    "accent_bg": "#22c55e14",
    "user_bubble": "#16a34a",
    "user_text": "#ffffff",
    "ai_bubble": "#ffffff",
    "ai_text": "#1e293b",
    "input_bg": "#ffffff",
    "green_50": "#f0fdf4",
    "green_100": "#dcfce7",
    "card_shadow": "#0000001a",
}

THEME_LIGHT_BLUE = {
    "name": "Light Blue & Warm",
    "bg": "#faf7f4",
    "surface": "#ffffff",
    "surface2": "#f3f0ec",
    "surface3": "#e8e4df",
    "border": "#e2d5be",
    "text": "#2d2640",
    "text_muted": "#8a7a66",
    "accent": "#3b82f6",
    "accent_dark": "#2563eb",
    "accent_dim": "#60a5fa",
    "accent_bg": "#3b82f614",
    "user_bubble": "#2563eb",
    "user_text": "#ffffff",
    "ai_bubble": "#ffffff",
    "ai_text": "#2d2640",
    "input_bg": "#ffffff",
    "mint": "#6ec9a8",
    "mint_bg": "#6ec9a81a",
    "card_shadow": "#0000001a",
}

def c(theme, key):
    """Get a Sketch color from a theme dict."""
    return hex_to_sketch_color(theme[key])

def ca(theme, key, alpha):
    """Get a Sketch color from a theme dict with custom alpha."""
    return with_alpha(hex_to_sketch_color(theme[key]), alpha)


# ============================================================
# CONSTANTS
# ============================================================
AW = 1440  # artboard width

# Chat conversation data
AI_WELCOME = (
    "Hi there! I'm your Eco-Nudge assistant. I can help you with:\n"
    "• Finding sustainable recipe alternatives\n"
    "• Swapping high-carbon ingredients for eco-friendly ones\n"
    "• Understanding the environmental impact of your meals\n"
    "• Tips for reducing your food carbon footprint\n"
    "• Cooking techniques, meal planning, and nutrition advice\n\n"
    "What would you like to know?"
)

CONVERSATION = [
    ("user", "What are some good alternatives to beef for bolognese?"),
    ("ai", (
        "Great question! Here are some lower-carbon alternatives for bolognese:\n\n"
        "🌱 Lentils – 0.9 kg CO₂e/kg (vs 27 kg for beef!)\n"
        "🍄 Mushrooms – 1.3 kg CO₂e/kg, great meaty texture\n"
        "🫘 TVP (Textured Vegetable Protein) – 1.2 kg CO₂e/kg\n"
        "🐔 Chicken mince – 6.9 kg CO₂e/kg (75% less than beef)\n\n"
        "A lentil bolognese would save about 3.1 kg CO₂ per serving! "
        "Want me to show you a full recipe?"
    )),
    ("user", "Yes, show me the lentil bolognese recipe!"),
    ("ai", (
        "Here's my Eco Lentil Bolognese recipe:\n\n"
        "📋 Ingredients (4 servings):\n"
        "• 250g brown/green lentils\n"
        "• 400g canned tomatoes\n"
        "• 2 carrots, diced\n"
        "• 1 onion, diced\n"
        "• 3 garlic cloves\n"
        "• 2 tbsp olive oil\n"
        "• Fresh basil, salt, pepper\n"
        "• 400g spaghetti\n\n"
        "🌿 Carbon footprint: 0.38 kg CO₂e/serving\n"
        "That's 91% less than a traditional beef bolognese!"
    )),
]

QUICK_PROMPTS = [
    "🍽️ Low-carbon dinner",
    "🥩→🌱 Beef alternatives",
    "🍝 Greener pasta",
    "🧀 Cheese impact",
]


# ============================================================
# REUSABLE COMPONENT BUILDERS
# ============================================================

def build_nav(theme, nav_items, active_idx=2):
    """Top navigation bar. Returns (group, height). active_idx=2 → AI Assistant."""
    h = 56
    layers = []
    layers.append(make_rectangle("Nav BG", 0, 0, AW, h,
                                 fill_color=c(theme, "surface"),
                                 border_color=c(theme, "border")))
    # Brand
    layers.append(make_text("Brand Icon", "🌿", 32, 14, 28, 28,
                            font_size=20, color=c(theme, "accent")))
    layers.append(make_text("Brand Name", "Eco-Nudge", 64, 16, 160, 24,
                            font_size=18, font_name="PlayfairDisplay-Bold",
                            color=c(theme, "accent")))
    # Links
    lx = 360
    for i, item in enumerate(nav_items):
        is_active = (i == active_idx)
        col = c(theme, "accent") if is_active else c(theme, "text_muted")
        font = "Inter-SemiBold" if is_active else "Inter-Medium"
        iw = len(item) * 9 + 20
        if is_active:
            layers.append(make_rectangle(
                f"Active BG: {item}", lx - 10, 10, iw, 36,
                fill_color=ca(theme, "accent", 0.12), corner_radius=8))
        layers.append(make_text(f"Nav: {item}", item, lx, 18, iw - 10, 20,
                                font_size=14, font_name=font, color=col))
        lx += iw + 12
    # Streak
    sx = AW - 100
    layers.append(make_rectangle("Streak BG", sx, 12, 64, 32,
                                 fill_color=ca(theme, "accent", 0.12),
                                 corner_radius=16))
    layers.append(make_text("Streak", "🔥 3", sx + 12, 18, 40, 20,
                            font_size=13, font_name="Inter-SemiBold",
                            color=c(theme, "accent")))
    return make_group("Navigation Bar", 0, 0, AW, h, layers), h


def build_chat_header(theme, x, y, w, title="Eco-Nudge Assistant",
                      subtitle="Ready to help with sustainable meal planning",
                      avatar="🌿"):
    """Chat assistant header with avatar. Returns (group, next_y)."""
    h = 72
    layers = []
    # Avatar circle
    layers.append(make_rectangle("Avatar BG", 0, 0, 48, 48,
                                 fill_color=ca(theme, "accent", 0.15),
                                 corner_radius=24))
    layers.append(make_text("Avatar", avatar, 12, 10, 24, 28,
                            font_size=22, color=c(theme, "accent")))
    layers.append(make_text("Title", title, 64, 4, w - 80, 28,
                            font_size=20, font_name="Inter-SemiBold",
                            color=c(theme, "text")))
    layers.append(make_text("Subtitle", subtitle, 64, 32, w - 80, 18,
                            font_size=13, font_name="Inter-Regular",
                            color=c(theme, "accent")))
    layers.append(make_rectangle("Divider", 0, h - 1, w, 1,
                                 fill_color=c(theme, "border")))
    return make_group("Chat Header", x, y, w, h, layers), y + h + 16


def build_ai_bubble(theme, text, x, y, w, line_h=20, show_avatar=True):
    """AI assistant message bubble. Returns (group, next_y)."""
    lines = text.count('\n') + 1
    text_h = lines * line_h + 10
    bubble_h = text_h + 24
    full_h = bubble_h
    layers = []
    bx = 0
    if show_avatar:
        layers.append(make_rectangle("AI Avatar BG", 0, 0, 32, 32,
                                     fill_color=ca(theme, "accent", 0.15),
                                     corner_radius=16))
        layers.append(make_text("AI Avatar", "🌿", 8, 5, 16, 22,
                                font_size=14, color=c(theme, "accent")))
        bx = 44
    bubble_w = w - bx - 60
    layers.append(make_rectangle("AI Bubble", bx, 0, bubble_w, bubble_h,
                                 fill_color=c(theme, "ai_bubble"),
                                 border_color=c(theme, "border"),
                                 corner_radius=16))
    layers.append(make_text("AI Text", text, bx + 16, 12, bubble_w - 32, text_h,
                            font_size=14, font_name="Inter-Regular",
                            color=c(theme, "ai_text"), line_height=line_h))
    return make_group("AI Message", x, y, w, full_h, layers), y + full_h + 12


def build_user_bubble(theme, text, x, y, w):
    """User message bubble (right-aligned). Returns (group, next_y)."""
    text_w = min(len(text) * 8 + 32, w - 100)
    bubble_h = 48 if len(text) < 60 else 72
    bx = w - text_w - 44
    layers = []
    # Avatar right
    layers.append(make_rectangle("User Avatar BG", w - 32, 0, 32, 32,
                                 fill_color=ca(theme, "text_muted", 0.2),
                                 corner_radius=16))
    layers.append(make_text("User Avatar", "👤", w - 24, 5, 16, 22,
                            font_size=14, color=c(theme, "text_muted")))
    # Bubble
    layers.append(make_rectangle("User Bubble", bx, 0, text_w, bubble_h,
                                 fill_color=c(theme, "user_bubble"),
                                 corner_radius=16))
    layers.append(make_text("User Text", text, bx + 16, 14, text_w - 32,
                            bubble_h - 28, font_size=14,
                            font_name="Inter-Regular",
                            color=c(theme, "user_text")))
    return make_group("User Message", x, y, w, bubble_h, layers), y + bubble_h + 12


def build_quick_prompts(theme, prompts, x, y, w):
    """Quick prompt pill buttons. Returns (group, next_y)."""
    layers = []
    px = 0
    row_h = 40
    for i, prompt in enumerate(prompts):
        pw = len(prompt) * 7.5 + 28
        if px + pw > w:
            px = 0
            row_h += 44
        layers.append(make_rectangle(
            f"Pill BG: {prompt[:20]}", px, row_h - 40, pw, 36,
            fill_color=ca(theme, "accent", 0.0),
            border_color=ca(theme, "text_muted", 0.35),
            corner_radius=18))
        layers.append(make_text(
            f"Pill: {prompt[:20]}", prompt, px + 14, row_h - 32, pw - 28, 20,
            font_size=13, font_name="Inter-Medium",
            color=c(theme, "text_muted")))
        px += pw + 10
    return make_group("Quick Prompts", x, y, w, row_h, layers), y + row_h + 16


def build_chat_input(theme, x, y, w, placeholder="Ask me anything about sustainable eating...",
                     pill_shape=True):
    """Chat input bar with send button. Returns (group, next_y)."""
    h = 52
    cr = 26 if pill_shape else 12
    layers = []
    layers.append(make_rectangle("Input BG", 0, 0, w - 56, h,
                                 fill_color=c(theme, "input_bg"),
                                 border_color=c(theme, "border"),
                                 corner_radius=cr))
    layers.append(make_text("Placeholder", placeholder, 20, 16, w - 120, 20,
                            font_size=14, font_name="Inter-Regular",
                            color=c(theme, "text_muted")))
    # Send button
    layers.append(make_rectangle("Send BG", w - 48, 4, 44, 44,
                                 fill_color=c(theme, "accent_dark"),
                                 corner_radius=22))
    layers.append(make_text("Send Icon", "➤", w - 36, 16, 20, 20,
                            font_size=16, font_name="Inter-Bold",
                            color=hex_to_sketch_color("#ffffff"), alignment=2))
    return make_group("Chat Input", x, y, w, h, layers), y + h + 16


def build_typing_indicator(theme, x, y, w):
    """Typing indicator dots. Returns (group, next_y)."""
    layers = []
    layers.append(make_rectangle("AI Avatar BG", 0, 0, 32, 32,
                                 fill_color=ca(theme, "accent", 0.15),
                                 corner_radius=16))
    layers.append(make_text("AI Avatar", "🌿", 8, 5, 16, 22,
                            font_size=14, color=c(theme, "accent")))
    layers.append(make_rectangle("Dots BG", 44, 0, 80, 36,
                                 fill_color=c(theme, "ai_bubble"),
                                 border_color=c(theme, "border"),
                                 corner_radius=18))
    for i in range(3):
        layers.append(make_rectangle(
            f"Dot {i}", 62 + i * 16, 14, 8, 8,
            fill_color=ca(theme, "text_muted", 0.5 + i * 0.15),
            corner_radius=4))
    return make_group("Typing Indicator", x, y, w, 36, layers), y + 48


# ============================================================
# SKETCH 1: Dark Classic Chat (matches index.html)
# ============================================================

def build_sketch_ai_01():
    """Dark theme, classic centered chat — faithful to index.html layout."""
    T = THEME_DARK_GREEN
    nav_items = ["Meal Planner", "AI Assistant", "My Recipes", "My Impact", "Settings"]
    layers = []

    # Nav
    nav, y = build_nav(T, nav_items, active_idx=1)
    layers.append(nav)
    y += 32

    # Chat container (max-width 800px centered)
    chat_w = 800
    cx = (AW - chat_w) // 2

    # Chat header
    hdr, y = build_chat_header(T, cx, y, chat_w)
    layers.append(hdr)

    # AI welcome message
    ai_msg, y = build_ai_bubble(T, AI_WELCOME, cx, y, chat_w)
    layers.append(ai_msg)

    # Conversation
    for role, text in CONVERSATION:
        if role == "user":
            msg, y = build_user_bubble(T, text, cx, y, chat_w)
        else:
            msg, y = build_ai_bubble(T, text, cx, y, chat_w)
        layers.append(msg)

    # Typing indicator
    typing, y = build_typing_indicator(T, cx, y, chat_w)
    layers.append(typing)
    y += 16

    # Quick prompts
    prompts, y = build_quick_prompts(T, QUICK_PROMPTS, cx, y, chat_w)
    layers.append(prompts)

    # Chat input (sticky at bottom)
    inp, y = build_chat_input(T, cx, y, chat_w)
    layers.append(inp)

    ab = make_artboard("AI-Assistant-01-Dark-Classic-Chat", AW, int(y + 40),
                       c(T, "bg"), layers)
    return ab


# ============================================================
# SKETCH 2: Light Sidebar Context Panel
# ============================================================

def build_sketch_ai_02():
    """Light theme, chat on right with context sidebar on left."""
    T = THEME_LIGHT_GREEN
    nav_items = ["Meal Planner", "AI Assistant", "My Recipes", "My Impact", "Settings"]
    layers = []

    nav, y = build_nav(T, nav_items, active_idx=1)
    layers.append(nav)
    y += 24

    # --- Left sidebar (320px) ---
    sidebar_w = 340
    sx = 40
    main_x = sx + sidebar_w + 32
    chat_w = AW - main_x - 40

    # Sidebar card background
    sb_h = 900
    layers.append(make_rectangle("Sidebar BG", sx, y, sidebar_w, sb_h,
                                 fill_color=c(T, "surface"),
                                 border_color=c(T, "border"),
                                 corner_radius=16,
                                 shadows=[make_shadow(
                                     hex_to_sketch_color(T["card_shadow"]),
                                     0, 2, 12)]))

    sy = y + 24
    # Sidebar title
    layers.append(make_text("SB Title", "💬 Conversation Context", sx + 20, sy,
                            sidebar_w - 40, 24, font_size=16,
                            font_name="Inter-SemiBold", color=c(T, "text")))
    sy += 36

    # Recent topics section
    layers.append(make_text("SB Section", "RECENT TOPICS", sx + 20, sy,
                            sidebar_w - 40, 16, font_size=11,
                            font_name="Inter-Bold", color=c(T, "text_muted")))
    sy += 28
    topics = [
        ("Beef alternatives", "12 min ago", "🥩"),
        ("Lentil bolognese recipe", "8 min ago", "🍝"),
        ("Seasonal vegetables", "Yesterday", "🥕"),
        ("Carbon footprint basics", "2 days ago", "🌍"),
    ]
    for title, time, emoji in topics:
        layers.append(make_rectangle(
            f"Topic BG: {title}", sx + 12, sy, sidebar_w - 24, 56,
            fill_color=c(T, "surface2"), corner_radius=10))
        layers.append(make_text(f"Emoji: {title}", emoji, sx + 24, sy + 8,
                                20, 20, font_size=16, color=c(T, "text")))
        layers.append(make_text(f"Topic: {title}", title, sx + 52, sy + 8,
                                sidebar_w - 80, 18, font_size=14,
                                font_name="Inter-Medium", color=c(T, "text")))
        layers.append(make_text(f"Time: {title}", time, sx + 52, sy + 30,
                                sidebar_w - 80, 14, font_size=12,
                                font_name="Inter-Regular",
                                color=c(T, "text_muted")))
        sy += 64

    sy += 16
    # Eco Tip
    layers.append(make_text("Tip Section", "💡 ECO TIP", sx + 20, sy,
                            sidebar_w - 40, 16, font_size=11,
                            font_name="Inter-Bold", color=c(T, "text_muted")))
    sy += 28
    layers.append(make_rectangle("Tip Card BG", sx + 12, sy, sidebar_w - 24, 100,
                                 fill_color=hex_to_sketch_color(
                                     T.get("green_50", "#f0fdf4")),
                                 border_color=ca(T, "accent", 0.3),
                                 corner_radius=12))
    layers.append(make_text("Tip Text",
                            "Seasonal vegetables have up to 50% lower "
                            "carbon footprint than out-of-season imports. "
                            "Try local farmers' markets!",
                            sx + 24, sy + 12, sidebar_w - 48, 76,
                            font_size=13, font_name="Inter-Regular",
                            color=c(T, "text"), line_height=20))
    sy += 120

    # Quick stats
    layers.append(make_text("Stats Section", "📊 YOUR IMPACT", sx + 20, sy,
                            sidebar_w - 40, 16, font_size=11,
                            font_name="Inter-Bold", color=c(T, "text_muted")))
    sy += 28
    stats = [("12.4 kg", "CO₂ Saved"), ("23", "Meals"), ("15", "Swaps")]
    stat_w = (sidebar_w - 36) // 3
    for i, (val, label) in enumerate(stats):
        stx = sx + 12 + i * stat_w
        layers.append(make_rectangle(
            f"Stat BG: {label}", stx, sy, stat_w - 8, 64,
            fill_color=c(T, "surface2"), corner_radius=10))
        layers.append(make_text(f"Stat: {val}", val, stx + 8, sy + 10,
                                stat_w - 16, 24, font_size=18,
                                font_name="Inter-Bold",
                                color=c(T, "accent_dark"), alignment=2))
        layers.append(make_text(f"Stat Label: {label}", label, stx + 8, sy + 38,
                                stat_w - 16, 16, font_size=11,
                                font_name="Inter-Regular",
                                color=c(T, "text_muted"), alignment=2))

    # --- Main chat area ---
    hdr, cy = build_chat_header(T, main_x, y, chat_w)
    layers.append(hdr)

    ai_msg, cy = build_ai_bubble(T, AI_WELCOME, main_x, cy, chat_w)
    layers.append(ai_msg)

    for role, text in CONVERSATION:
        if role == "user":
            msg, cy = build_user_bubble(T, text, main_x, cy, chat_w)
        else:
            msg, cy = build_ai_bubble(T, text, main_x, cy, chat_w)
        layers.append(msg)

    prompts, cy = build_quick_prompts(T, QUICK_PROMPTS, main_x, cy, chat_w)
    layers.append(prompts)

    inp, cy = build_chat_input(T, main_x, cy, chat_w)
    layers.append(inp)

    total_h = max(cy, y + sb_h) + 40
    ab = make_artboard("AI-Assistant-02-Light-Sidebar-Context", AW,
                       int(total_h), c(T, "bg"), layers)
    return ab


# ============================================================
# SKETCH 3: Dark Split Panel (history sidebar + chat)
# ============================================================

def build_sketch_ai_03():
    """Dark purple-teal theme with conversation history sidebar."""
    T = THEME_DARK_PURPLE
    nav_items = ["Meal Planner", "AI Assistant", "My Recipes", "My Impact"]
    layers = []

    nav, y = build_nav(T, nav_items, active_idx=1)
    layers.append(nav)

    # Left panel: conversation history (280px, full height)
    panel_w = 280
    panel_h = 950
    layers.append(make_rectangle("History Panel BG", 0, y, panel_w, panel_h,
                                 fill_color=c(T, "surface"),
                                 border_color=c(T, "border")))

    py_ = y + 20
    layers.append(make_text("History Title", "Conversations", 20, py_,
                            panel_w - 40, 24, font_size=16,
                            font_name="Inter-SemiBold", color=c(T, "text")))
    py_ += 36

    # New chat button
    layers.append(make_rectangle("New Chat BG", 16, py_, panel_w - 32, 40,
                                 fill_color=c(T, "accent_dark"),
                                 corner_radius=10))
    layers.append(make_text("New Chat", "+ New Chat", 16, py_ + 10,
                            panel_w - 32, 20, font_size=14,
                            font_name="Inter-SemiBold",
                            color=hex_to_sketch_color("#ffffff"), alignment=2))
    py_ += 56

    # Search
    layers.append(make_rectangle("Search BG", 16, py_, panel_w - 32, 36,
                                 fill_color=c(T, "surface2"),
                                 border_color=c(T, "border"),
                                 corner_radius=8))
    layers.append(make_text("Search", "🔍 Search chats...", 28, py_ + 8,
                            panel_w - 60, 20, font_size=13,
                            font_name="Inter-Regular", color=c(T, "text_muted")))
    py_ += 48

    # Section: Today
    layers.append(make_text("Section Today", "TODAY", 20, py_, panel_w - 40, 14,
                            font_size=11, font_name="Inter-Bold",
                            color=c(T, "text_muted")))
    py_ += 22

    convos_today = [
        ("Beef alternatives & lentil recipe", True),
        ("Seasonal shopping list", False),
        ("Low-carbon meal prep", False),
    ]
    for title, active in convos_today:
        bg_col = ca(T, "accent", 0.15) if active else ca(T, "surface2", 0.0)
        border_left_col = c(T, "accent") if active else None
        layers.append(make_rectangle(
            f"Conv BG: {title[:20]}", 8, py_, panel_w - 16, 48,
            fill_color=bg_col, corner_radius=8))
        if active:
            layers.append(make_rectangle("Active Indicator", 8, py_ + 8,
                                         3, 32, fill_color=c(T, "accent"),
                                         corner_radius=2))
        tcol = c(T, "accent") if active else c(T, "text")
        layers.append(make_text(f"Conv: {title[:20]}", title[:30],
                                24, py_ + 8, panel_w - 48, 16,
                                font_size=13, font_name="Inter-Medium",
                                color=tcol))
        layers.append(make_text(f"Conv Time", "2 messages" if active else "4 messages",
                                24, py_ + 28, panel_w - 48, 12,
                                font_size=11, font_name="Inter-Regular",
                                color=c(T, "text_muted")))
        py_ += 56

    py_ += 8
    layers.append(make_text("Section Yest", "YESTERDAY", 20, py_,
                            panel_w - 40, 14, font_size=11,
                            font_name="Inter-Bold", color=c(T, "text_muted")))
    py_ += 22
    older_convos = [
        "Carbon footprint of dairy",
        "Vegan meal ideas for kids",
        "Composting tips",
    ]
    for title in older_convos:
        layers.append(make_rectangle(
            f"Conv BG: {title[:20]}", 8, py_, panel_w - 16, 48,
            fill_color=ca(T, "surface2", 0.0), corner_radius=8))
        layers.append(make_text(f"Conv: {title[:20]}", title,
                                24, py_ + 8, panel_w - 48, 16,
                                font_size=13, font_name="Inter-Medium",
                                color=c(T, "text")))
        layers.append(make_text("Time", "3 messages", 24, py_ + 28,
                                panel_w - 48, 12, font_size=11,
                                font_name="Inter-Regular",
                                color=c(T, "text_muted")))
        py_ += 56

    # --- Main chat (right side) ---
    chat_x = panel_w + 32
    chat_w = AW - panel_w - 72

    cy = y + 24
    hdr, cy = build_chat_header(T, chat_x, cy, chat_w,
                                title="Beef Alternatives & Lentil Recipe",
                                subtitle="Active conversation · 2 messages")
    layers.append(hdr)

    # Model selector pill
    model_y = cy - 8
    layers.append(make_rectangle("Model Pill", chat_x, model_y, 200, 32,
                                 fill_color=c(T, "surface2"),
                                 border_color=c(T, "border"),
                                 corner_radius=16))
    layers.append(make_text("Model", "🤖 qwen3:4b · Local", chat_x + 12,
                            model_y + 7, 176, 18, font_size=12,
                            font_name="Inter-Medium", color=c(T, "text_muted")))

    teal = hex_to_sketch_color(T["teal"])
    layers.append(make_rectangle("Online Dot", chat_x + 180, model_y + 12, 8, 8,
                                 fill_color=teal, corner_radius=4))
    cy = model_y + 44

    # Messages
    ai_msg, cy = build_ai_bubble(T, AI_WELCOME, chat_x, cy, chat_w)
    layers.append(ai_msg)

    for role, text in CONVERSATION:
        if role == "user":
            msg, cy = build_user_bubble(T, text, chat_x, cy, chat_w)
        else:
            msg, cy = build_ai_bubble(T, text, chat_x, cy, chat_w)
        layers.append(msg)

    typing, cy = build_typing_indicator(T, chat_x, cy, chat_w)
    layers.append(typing)
    cy += 16

    prompts, cy = build_quick_prompts(T, QUICK_PROMPTS, chat_x, cy, chat_w)
    layers.append(prompts)

    inp, cy = build_chat_input(T, chat_x, cy, chat_w,
                               placeholder="Message Eco-Nudge AI...")
    layers.append(inp)

    total_h = max(cy, y + panel_h) + 40
    ab = make_artboard("AI-Assistant-03-Dark-Split-Panel", AW,
                       int(total_h), c(T, "bg"), layers)
    return ab


# ============================================================
# SKETCH 4: Light Cards-Based Chat (interactive inline cards)
# ============================================================

def build_sketch_ai_04():
    """Light blue/warm theme with inline interactive cards in chat."""
    T = THEME_LIGHT_BLUE
    nav_items = ["Meal Planner", "AI Assistant", "My Recipes", "My Impact", "Settings"]
    layers = []

    nav, y = build_nav(T, nav_items, active_idx=1)
    layers.append(nav)
    y += 24

    chat_w = 860
    cx = (AW - chat_w) // 2

    # Header with extra features
    hdr, y = build_chat_header(T, cx, y, chat_w,
                               title="Eco-Nudge Assistant",
                               subtitle="Powered by local AI · Privacy-first")
    layers.append(hdr)

    # --- Welcome message ---
    welcome_short = (
        "Hi! I'm your eco-cooking assistant. Ask me anything about "
        "sustainable eating, or try one of the quick actions below!"
    )
    ai_msg, y = build_ai_bubble(T, welcome_short, cx, y, chat_w)
    layers.append(ai_msg)

    # --- Quick action cards (inline, horizontal) ---
    card_w = (chat_w - 44 - 36) // 3
    card_h = 120
    card_y = y
    action_cards = [
        ("🍽️", "Meal Planner", "Get a personalized low-carbon\nmeal plan for the week"),
        ("🔄", "Ingredient Swap", "Find greener alternatives\nfor any ingredient"),
        ("📊", "Impact Check", "Analyze the carbon footprint\nof your favorite recipe"),
    ]
    card_layers = []
    for i, (emoji, title, desc) in enumerate(action_cards):
        cax = 44 + i * (card_w + 18)
        card_layers.append(make_rectangle(
            f"Action Card: {title}", cax, 0, card_w, card_h,
            fill_color=c(T, "surface"),
            border_color=c(T, "border"),
            corner_radius=14,
            shadows=[make_shadow(hex_to_sketch_color(T["card_shadow"]), 0, 2, 8)]))
        card_layers.append(make_text(f"Emoji: {title}", emoji, cax + 16, 16,
                                     40, 32, font_size=28, color=c(T, "accent")))
        card_layers.append(make_text(f"Title: {title}", title, cax + 16, 52,
                                     card_w - 32, 20, font_size=14,
                                     font_name="Inter-SemiBold",
                                     color=c(T, "text")))
        card_layers.append(make_text(f"Desc: {title}", desc, cax + 16, 74,
                                     card_w - 32, 36, font_size=12,
                                     font_name="Inter-Regular",
                                     color=c(T, "text_muted"), line_height=18))
    layers.append(make_group("Action Cards", cx, y, chat_w, card_h, card_layers))
    y += card_h + 20

    # --- User message ---
    umsg, y = build_user_bubble(
        T, "What are the best alternatives to beef for bolognese?", cx, y, chat_w)
    layers.append(umsg)

    # --- AI response with inline swap comparison card ---
    ai_intro = (
        "Great question! Here are some eco-friendly bolognese alternatives, "
        "ranked by carbon savings:"
    )
    ai_msg2, y = build_ai_bubble(T, ai_intro, cx, y, chat_w, show_avatar=True)
    layers.append(ai_msg2)

    # Inline comparison card
    comp_w = chat_w - 60
    comp_h = 280
    comp_x = cx + 44
    comp_layers = []
    comp_layers.append(make_rectangle("Comp Card BG", 0, 0, comp_w, comp_h,
                                      fill_color=c(T, "surface"),
                                      border_color=c(T, "border"),
                                      corner_radius=14,
                                      shadows=[make_shadow(
                                          hex_to_sketch_color(T["card_shadow"]),
                                          0, 2, 12)]))
    comp_layers.append(make_text("Comp Title", "🔄 Ingredient Alternatives",
                                 16, 16, comp_w - 32, 22, font_size=16,
                                 font_name="Inter-SemiBold", color=c(T, "text")))
    comp_layers.append(make_rectangle("Comp Divider", 16, 48, comp_w - 32, 1,
                                      fill_color=c(T, "border")))

    alternatives = [
        ("🌱 Lentils", "0.9 kg CO₂/kg", "−97%", "#16a34a"),
        ("🍄 Mushrooms", "1.3 kg CO₂/kg", "−95%", "#16a34a"),
        ("🫘 TVP", "1.2 kg CO₂/kg", "−96%", "#16a34a"),
        ("🐔 Chicken", "6.9 kg CO₂/kg", "−74%", "#f59e0b"),
    ]
    iy = 60
    for name, co2, saving, sav_color in alternatives:
        comp_layers.append(make_rectangle(
            f"Row BG: {name}", 12, iy, comp_w - 24, 46,
            fill_color=ca(T, "accent", 0.04), corner_radius=8))
        comp_layers.append(make_text(
            f"Alt: {name}", name, 24, iy + 4, 200, 20,
            font_size=14, font_name="Inter-Medium", color=c(T, "text")))
        comp_layers.append(make_text(
            f"CO2: {name}", co2, 24, iy + 26, 200, 16,
            font_size=12, font_name="Inter-Regular", color=c(T, "text_muted")))
        # Saving badge
        badge_w = 56
        comp_layers.append(make_rectangle(
            f"Badge: {name}", comp_w - 80, iy + 10, badge_w, 26,
            fill_color=hex_to_sketch_color(sav_color, 0.15),
            corner_radius=6))
        comp_layers.append(make_text(
            f"Saving: {name}", saving, comp_w - 80, iy + 14, badge_w, 18,
            font_size=13, font_name="Inter-Bold",
            color=hex_to_sketch_color(sav_color), alignment=2))
        iy += 52

    # "Use lentils" action button
    btn_w = 160
    comp_layers.append(make_rectangle(
        "Use Lentils Btn", comp_w // 2 - btn_w // 2, iy + 4, btn_w, 38,
        fill_color=c(T, "accent_dark"), corner_radius=10))
    comp_layers.append(make_text(
        "Btn Text", "🌱 Use Lentils", comp_w // 2 - btn_w // 2, iy + 13,
        btn_w, 20, font_size=14, font_name="Inter-SemiBold",
        color=hex_to_sketch_color("#ffffff"), alignment=2))

    layers.append(make_group("Comparison Card", comp_x, y, comp_w, comp_h,
                             comp_layers))
    y += comp_h + 16

    # --- AI follow-up text ---
    ai_followup = (
        "Lentils are the clear winner! A lentil bolognese saves ~3.1 kg CO₂ "
        "per serving. Shall I show you the full recipe?"
    )
    ai_msg3, y = build_ai_bubble(T, ai_followup, cx, y, chat_w)
    layers.append(ai_msg3)

    # --- User reply ---
    umsg2, y = build_user_bubble(T, "Yes please! Show me the recipe.", cx, y, chat_w)
    layers.append(umsg2)

    # --- Inline recipe card ---
    recipe_w = chat_w - 60
    recipe_h = 220
    recipe_x = cx + 44
    rl = []
    rl.append(make_rectangle("Recipe Card BG", 0, 0, recipe_w, recipe_h,
                             fill_color=c(T, "surface"),
                             border_color=c(T, "border"),
                             corner_radius=14,
                             shadows=[make_shadow(
                                 hex_to_sketch_color(T["card_shadow"]),
                                 0, 2, 12)]))
    # Image placeholder
    rl.append(make_rectangle("Recipe Img", 0, 0, 180, recipe_h,
                             fill_color=hex_to_sketch_color("#e5e7eb"),
                             corner_radius=0))
    rl.append(make_text("Img Label", "📷", 78, recipe_h // 2 - 10, 24, 24,
                         font_size=20, color=c(T, "text_muted")))
    # Recipe details
    rx = 200
    rl.append(make_text("Recipe Title", "🌱 Eco Lentil Bolognese", rx, 16,
                         recipe_w - rx - 16, 24, font_size=17,
                         font_name="Inter-SemiBold", color=c(T, "text")))
    rl.append(make_text("Recipe Meta", "4 servings · 40 min · Mediterranean",
                         rx, 44, recipe_w - rx - 16, 18, font_size=13,
                         font_name="Inter-Regular", color=c(T, "text_muted")))

    # Carbon badge
    rl.append(make_rectangle("Carbon Badge BG", rx, 72, 190, 28,
                             fill_color=hex_to_sketch_color("#16a34a", 0.12),
                             corner_radius=6))
    rl.append(make_text("Carbon", "🌿 0.38 kg CO₂e/serving · 91% less!",
                         rx + 8, 77, 174, 18, font_size=12,
                         font_name="Inter-SemiBold",
                         color=hex_to_sketch_color("#16a34a")))

    rl.append(make_text("Ingredients",
                         "Lentils, tomatoes, carrots, onion,\ngarlic, olive oil, basil, spaghetti",
                         rx, 110, recipe_w - rx - 16, 36, font_size=13,
                         font_name="Inter-Regular", color=c(T, "text_muted"),
                         line_height=18))

    # Action buttons
    rl.append(make_rectangle("Open Btn", rx, recipe_h - 52, 120, 36,
                             fill_color=c(T, "accent_dark"), corner_radius=8))
    rl.append(make_text("Open Btn Text", "📋 Open Recipe", rx, recipe_h - 44,
                         120, 20, font_size=13, font_name="Inter-SemiBold",
                         color=hex_to_sketch_color("#ffffff"), alignment=2))
    rl.append(make_rectangle("Save Btn", rx + 130, recipe_h - 52, 100, 36,
                             border_color=c(T, "border"), corner_radius=8))
    rl.append(make_text("Save Btn Text", "💾 Save", rx + 130, recipe_h - 44,
                         100, 20, font_size=13, font_name="Inter-Medium",
                         color=c(T, "text"), alignment=2))

    layers.append(make_group("Recipe Card", recipe_x, y, recipe_w, recipe_h, rl))
    y += recipe_h + 24

    # Quick prompts
    prompts, y = build_quick_prompts(T, QUICK_PROMPTS, cx, y, chat_w)
    layers.append(prompts)

    # Chat input
    inp, y = build_chat_input(T, cx, y, chat_w)
    layers.append(inp)

    ab = make_artboard("AI-Assistant-04-Light-Cards-Interactive", AW,
                       int(y + 40), c(T, "bg"), layers)
    return ab


# ============================================================
# DESIGN TOKENS ARTBOARD
# ============================================================

def build_tokens_artboard(theme, sketch_name):
    """Build a design tokens reference artboard for a theme."""
    layers = []
    y = 40
    blk = hex_to_sketch_color("#333333")
    gray = hex_to_sketch_color("#999999")
    dgray = hex_to_sketch_color("#666666")

    layers.append(make_text("Title", f"Design Tokens — {sketch_name}",
                            40, y, 900, 36, font_size=24,
                            font_name="Inter-Bold", color=blk))
    y += 60

    layers.append(make_text("Section", "COLOR PALETTE", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32

    swatch_size = 56
    col_w = swatch_size + 130
    max_cols = 5
    col_idx = 0

    for var_name, var_value in theme.items():
        if var_name == "name":
            continue
        if not var_value.startswith('#'):
            continue
        sx = 40 + col_idx * col_w
        color = hex_to_sketch_color(var_value)
        layers.append(make_rectangle(f"Swatch: {var_name}", sx, y,
                                     swatch_size, swatch_size,
                                     fill_color=color,
                                     border_color=hex_to_sketch_color("#dddddd"),
                                     corner_radius=8))
        layers.append(make_text(f"Name: {var_name}", var_name, sx,
                                y + swatch_size + 4, col_w, 14, font_size=10,
                                font_name="Inter-Medium", color=dgray))
        layers.append(make_text(f"Val: {var_name}", var_value, sx,
                                y + swatch_size + 18, col_w, 12, font_size=9,
                                font_name="Inter-Regular", color=gray))
        col_idx += 1
        if col_idx >= max_cols:
            col_idx = 0
            y += swatch_size + 48

    y += swatch_size + 64

    layers.append(make_text("Section", "TYPOGRAPHY", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32
    specimens = [
        ("Display / H1", "PlayfairDisplay-Bold", 28),
        ("Heading / H2", "Inter-SemiBold", 20),
        ("Body / Regular", "Inter-Regular", 14),
        ("Body / Medium", "Inter-Medium", 14),
        ("Caption / Small", "Inter-Regular", 12),
        ("Button Text", "Inter-SemiBold", 14),
        ("Chat Message", "Inter-Regular", 14),
    ]
    for label, font, size in specimens:
        h = int(size * 1.6)
        layers.append(make_text(f"Type: {label}",
                                f"{label}  —  {font} @ {size}px",
                                40, y, 700, h, font_size=size,
                                font_name=font, color=blk))
        y += h + 12

    y += 40
    layers.append(make_text("Section", "COMPONENT SPECS", 40, y, 400, 20,
                            font_size=12, font_name="Inter-Bold", color=gray))
    y += 32
    specs = [
        "Chat bubble corner radius: 16px",
        "Card corner radius: 14px",
        "Input pill corner radius: 26px",
        "Avatar size: 48px (header), 32px (messages)",
        "Message max width: 80% of container",
        "Quick prompt pills: height 36px, radius 18px",
        "Send button: 44×44px, full round",
    ]
    for spec in specs:
        layers.append(make_text(f"Spec", spec, 40, y, 700, 20,
                                font_size=13, font_name="Inter-Regular",
                                color=blk))
        y += 24

    return make_artboard("Design Tokens", 1440, max(y + 40, 600),
                         bg_color=hex_to_sketch_color("#ffffff"), layers=layers)


# ============================================================
# MAIN
# ============================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output-sketch')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 64)
    print("  AI Assistant View — Sketch File Generator")
    print("=" * 64)
    print(f"  Output: {output_dir}\n")

    sketches = [
        ("ai-assistant-01-dark-classic-chat", build_sketch_ai_01,
         THEME_DARK_GREEN),
        ("ai-assistant-02-light-sidebar-context", build_sketch_ai_02,
         THEME_LIGHT_GREEN),
        ("ai-assistant-03-dark-split-panel", build_sketch_ai_03,
         THEME_DARK_PURPLE),
        ("ai-assistant-04-light-cards-interactive", build_sketch_ai_04,
         THEME_LIGHT_BLUE),
    ]

    results = []
    for filename, builder, theme in sketches:
        print(f"  Building: {filename}")
        try:
            main_ab = builder()
            tokens_ab = build_tokens_artboard(theme, filename)
            tokens_ab["frame"]["x"] = AW + 100
            page = make_page("Page 1", [main_ab, tokens_ab])
            output_path = os.path.join(output_dir, f"{filename}.sketch")
            write_sketch_file(output_path, page)
            results.append(output_path)
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 64}")
    print(f"  Done! Created {len(results)} .sketch file(s).")
    print()
    print("  Open in: Sketch, Figma (Import), Lunacy, or Penpot")
    print(f"{'=' * 64}")


if __name__ == '__main__':
    main()
