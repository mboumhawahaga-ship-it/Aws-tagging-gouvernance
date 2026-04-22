REQUIRED_TAGS = ["Owner", "Squad", "CostCenter", "Environment"]


def check_tags(tags: list) -> tuple[bool, list]:
    keys = [t.get("Key") for t in tags] if tags else []
    missing = [t for t in REQUIRED_TAGS if t not in keys]
    return len(missing) == 0, missing


def get_tag_value(tags: list, key: str) -> str:
    for t in tags:
        if t.get("Key") == key:
            return t.get("Value", "")
    return ""
