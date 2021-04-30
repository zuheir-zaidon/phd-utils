from phd_utils import third_party as subject


def test_grouper():
    i = [1, 2, 3]

    grouped = subject.grouper(iterable=i, group_size=2)

    grouped = list(map(list, grouped))

    assert grouped == [[1, 2], [3]]
