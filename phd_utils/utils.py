import itertools
import pprint
from typing import Iterable


def grouper(iterable: Iterable, group_size: int):
    """
    Split an iterable into group_size groups
    https://stackoverflow.com/a/8998040/9838189
    """

    it = iter(iterable)
    while True:
        chunk_it = itertools.islice(it, group_size)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)


def pformat(
    object,
    indent=1,
    width=80,
    depth=None,
    *,
    compact=False,
    sort_dicts=True,
    maxlen: int = 10
):
    if isinstance(object, list) and len(object) > maxlen:
        tail = object[-1]
        object = object[: maxlen - 2]
        object.append("...")
        object.append(tail)

    return pprint.pformat(
        object, indent=1, width=80, depth=None, compact=False, sort_dicts=True
    )
