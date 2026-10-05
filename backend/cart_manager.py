from .menu_manager import get_menu

def validate_items(items):
    menu = get_menu()
    products = {p["id"]: p for p in menu["products"]}
    options = menu["options"]
    clean = []
    for item in items:
        if not isinstance(item, dict): raise ValueError("Invalid order item")
        product = products.get(item.get("productId"))
        if not product or not product.get("available", False): raise ValueError("This drink is unavailable")
        quantity = item.get("quantity")
        if type(quantity) is not int or not 1 <= quantity <= 20: raise ValueError("Quantity must be between 1 and 20")
        supplied = item.get("options") or {}
        safe_options = {}; labels = {}
        for group in product["customizations"]:
            available = options[group]
            if group == "addons":
                ids = supplied.get(group, [])
                if not isinstance(ids, list) or len(ids) != len(set(ids)): raise ValueError("Invalid add-ons")
                selected = [o for o in available if o["id"] in ids]
                if len(selected) != len(ids): raise ValueError("Invalid add-on selection")
                safe_options[group] = [o["id"] for o in selected]; labels[group] = [o["label"] for o in selected]
            else:
                selected = next((o for o in available if o["id"] == supplied.get(group)), None)
                if not selected: raise ValueError(f"Invalid {group} selection")
                safe_options[group] = selected["id"]; labels[group] = selected["label"]
        unit_price = round(product["price"] + sum(opt["price"] for group, value in safe_options.items()
            for opt in options[group] if opt["id"] in (value if isinstance(value, list) else [value])), 2)
        clean.append({"productId":product["id"], "name":product["name"], "image":product["image"],
                      "quantity":quantity, "unitPrice":unit_price, "options":safe_options, "optionLabels":labels})
    return clean, menu.get("fees", {}).get("service", 0)
