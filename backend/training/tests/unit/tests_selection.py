from uuid import uuid4

import pytest

from grpc_client.models import TrainingLine
from services.selection import TrainingSelector


def make_line(
    *,
    parent_id=None,
    moves=None,
    analytic_version=1,
):
    return TrainingLine(
        id=uuid4(),
        parent_id=parent_id,
        tag=None,
        moves=moves or ['e2e4'],
        analytic_version=analytic_version,
    )


def test_select_single_root_without_children():
    root = make_line(moves=['e2e4'])

    result = TrainingSelector().select(
        [root],
        [],
    )

    assert result.lines == [root]
    assert result.moves == ['e2e4']


def test_select_flattens_moves_across_lines():
    root = make_line(moves=['e2e4'])
    child = make_line(
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
    )

    result = TrainingSelector().select(
        [root, child],
        [],
    )

    assert result.lines == [root, child]
    assert result.moves == [
        'e2e4',
        'e7e5',
        'g1f3',
    ]


def test_select_raises_when_tree_has_no_root():
    parent_id = uuid4()

    line = make_line(parent_id=parent_id)

    with pytest.raises(
        ValueError,
        match='Training tree has no root',
    ):
        TrainingSelector().select([line], [])


def test_line_priority_without_stats():
    selector = TrainingSelector()

    line = make_line()

    assert selector._line_priority(
        line,
        {},
    ) == 1.0


def test_line_priority_without_attempts():
    selector = TrainingSelector()

    line = make_line()

    stats = {
        (line.id, line.analytic_version): type(
            'Stats',
            (),
            {
                'attempts': 0,
                'fails': 0,
            },
        )(),
    }

    assert selector._line_priority(line, stats) == 1.0


def test_line_priority_with_all_failures():
    selector = TrainingSelector()

    line = make_line()

    stats = {
        (line.id, line.analytic_version): type(
            'Stats',
            (),
            {
                'attempts': 10,
                'fails': 10,
            },
        )(),
    }

    assert selector._line_priority(line, stats) == 1.0


def test_line_priority_with_successful_attempts():
    selector = TrainingSelector()

    line = make_line()

    stats = {
        (line.id, line.analytic_version): type(
            'Stats',
            (),
            {
                'attempts': 10,
                'fails': 0,
            },
        )(),
    }

    assert selector._line_priority(
        line,
        stats,
    ) == pytest.approx(0.5)


def test_subtree_priority_uses_max_priority(monkeypatch):
    selector = TrainingSelector()

    root = make_line()
    child = make_line(parent_id=root.id)
    grandchild = make_line(parent_id=child.id)

    priorities = {
        root.id: 0.2,
        child.id: 0.5,
        grandchild.id: 0.9,
    }

    monkeypatch.setattr(
        selector,
        '_line_priority',
        lambda line, stats: priorities[line.id],
    )

    children_by_parent = {
        root.id: [child],
        child.id: [grandchild],
    }

    assert selector._subtree_priority(
        root,
        children_by_parent,
        {},
    ) == 0.9


def test_subtree_priority_returns_own_priority_for_leaf(
    monkeypatch,
):
    selector = TrainingSelector()

    line = make_line()

    monkeypatch.setattr(
        selector,
        '_line_priority',
        lambda line, stats: 0.7,
    )

    assert selector._subtree_priority(
        line,
        {},
        {},
    ) == 0.7


def test_select_uses_random_choice(monkeypatch):
    selector = TrainingSelector()

    root = make_line(moves=['root'])
    child1 = make_line(
        parent_id=root.id,
        moves=['child1'],
    )
    child2 = make_line(
        parent_id=root.id,
        moves=['child2'],
    )

    selected = []

    def fake_choices(items, weights, k):
        selected.append((items, weights, k))
        return [child2]

    monkeypatch.setattr(
        'services.selection.random.choices',
        fake_choices,
    )

    result = selector.select(
        [root, child1, child2],
        [],
    )

    assert result.lines == [
        root,
        child2,
    ]
    assert result.moves == [
        'root',
        'child2',
    ]
    assert selected[0][2] == 1


def test_select_uses_first_root():
    root1 = make_line(moves=['first'])
    root2 = make_line(moves=['second'])

    result = TrainingSelector().select(
        [root1, root2],
        [],
    )

    assert result.lines == [root1]
    assert result.moves == ['first']
