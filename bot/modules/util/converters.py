import re

MENTION_REGEX = re.compile(r"<@(!?)([0-9]*)>")


def format_list(items: list, seperator: str = "or", brackets: str = ""):
    if len(items) < 2:
        return f"{brackets}{items[0]}{brackets}"

    new_items = []
    for i in items:
        if not re.match(MENTION_REGEX, i):
            new_items.append(f"{brackets}{i}{brackets}")
        else:
            new_items.append(i)

    msg = ", ".join(list(new_items)[:-1]) + f" {seperator} " + list(new_items)[-1]
    return msg