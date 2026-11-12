def overlap(a,b):
    return not (a["effective_to"] and b["effective_from"] and a["effective_to"]<b["effective_from"]
             or b["effective_to"] and a["effective_from"] and b["effective_to"]<a["effective_from"])
