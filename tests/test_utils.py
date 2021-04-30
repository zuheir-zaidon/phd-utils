from phd_utils import utils as subject
import logging

logger = logging.getLogger(__name__)


def test_grouper():
    i = [1, 2, 3]

    grouped = subject.grouper(iterable=i, group_size=2)
    grouped = list(map(list, grouped))

    assert grouped == [[1, 2], [3]]


def test_pformat():
    l = [str(i) * 50 for i in range(1000)]

    assert len(subject.pformat(l).splitlines()) == 10
