import itertools
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
