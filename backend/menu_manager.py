import json
import math
import os
import re
import tempfile
from .config import MENU_PATH

CUSTOMIZATIONS = {"size", "temperature", "sugar", "milk", "addons"}

def _clean_categories(categories):
    if not isinstance(categories, list) or not categories:
        raise ValueError("Add at least one menu category")
    clean = []
    seen = set()
    for value in categories:
        name = str(value).strip()
        key = name.casefold()
        if not name or len(name) > 40:
            raise ValueError("Category names must be between 1 and 40 characters")
        if key in seen:
            raise ValueError(f"Category '{name}' is duplicated")
        clean.append(name)
        seen.add(key)
    return clean

def validate_menu(menu):
    if not isinstance(menu, dict) or not isinstance(menu.get("products"), list) or not menu["products"]:
        raise ValueError("Menu must include at least one product")
    if len(menu["products"]) > 100:
        raise ValueError("Menu cannot contain more than 100 products")
    if any(not isinstance(product, dict) for product in menu["products"]):
        raise ValueError("Each product must be an object")
    options = menu.get("options")
    if not isinstance(options, dict) or any(not isinstance(options.get(group), list) for group in CUSTOMIZATIONS):
        raise ValueError("Menu options are incomplete")
    categories = _clean_categories(menu.get("categories") or list(dict.fromkeys(p.get("category", "") for p in menu["products"])))
    category_keys = {c.casefold() for c in categories}
    product_ids = set()
    for product in menu["products"]:
        product_id = str(product.get("id", "")).strip()
        name = str(product.get("name", "")).strip()
        category = str(product.get("category", "")).strip()
        price = product.get("price")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,59}", product_id):
            raise ValueError("Product IDs may use lowercase letters, numbers, hyphens and underscores")
        if product_id in product_ids:
            raise ValueError(f"Product ID '{product_id}' is duplicated")
        product_ids.add(product_id)
        if not name or len(name) > 100 or len(str(product.get("description", ""))) > 500:
            raise ValueError("Product name or description is invalid")
        if category.casefold() not in category_keys:
            raise ValueError(f"Product '{name}' must use an existing category")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0 or price > 10000:
            raise ValueError(f"Product '{name}' needs a valid price")
        if not isinstance(product.get("image"), str) or len(product["image"]) > 1000:
            raise ValueError(f"Product '{name}' needs a valid image path")
        if not isinstance(product.get("available"), bool):
            raise ValueError(f"Product '{name}' availability must be on or off")
        groups = product.get("customizations", [])
        if (not isinstance(groups, list) or any(not isinstance(group, str) for group in groups)
                or len(groups) != len(set(groups)) or any(group not in CUSTOMIZATIONS for group in groups)):
            raise ValueError(f"Product '{name}' has an invalid customization group")
        for group in groups:
            if not options[group]:
                raise ValueError(f"Customization '{group}' needs at least one option")
    for group, values in options.items():
        if group not in CUSTOMIZATIONS or not isinstance(values, list):
            raise ValueError("Menu contains an invalid option group")
        ids = set()
        for option in values:
            if (not isinstance(option, dict) or not isinstance(option.get("id"), str)
                    or not option["id"].strip() or not isinstance(option.get("label"), str)
                    or not option["label"].strip()):
                raise ValueError(f"Menu option in '{group}' needs an ID and label")
            if option["id"] in ids:
                raise ValueError(f"Menu option '{option['id']}' is duplicated")
            ids.add(option["id"])
            price = option.get("price", 0)
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
                raise ValueError(f"Menu option '{option['label']}' has an invalid price")
    return {**menu, "categories": categories}

def get_menu():
    with MENU_PATH.open(encoding="utf-8") as f:
        menu = json.load(f)
    if not isinstance(menu.get("products"), list) or not menu.get("products"):
        raise ValueError("Menu must include at least one product")
    menu.setdefault("categories", list(dict.fromkeys(p.get("category", "") for p in menu["products"])))
    menu.setdefault("contact", {"name": "Brew & Co.", "email": "", "phone": "", "address": "", "hours": "", "website": ""})
    return menu

def save_menu(menu):
    clean = validate_menu(menu)
    MENU_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=MENU_PATH.parent,
                                         delete=False, suffix=".tmp") as stream:
            temporary = stream.name
            json.dump(clean, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, MENU_PATH)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return clean
