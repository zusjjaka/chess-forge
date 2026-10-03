from collections import defaultdict
from dataclasses import dataclass
from random import choices
from uuid import UUID

from core.constants import (
    CONFIDENCE_ATTEMPTS,
    SELECTION_BASE_WEIGHT,
    SELECTION_DIFFICULTY_WEIGHT,
)
from grpc_client.models import TrainingLine
from models.stat import LineTrainingStats


@dataclass(slots=True)
class SelectedPath:
    lines: list[TrainingLine]
    moves: list[str]


class TrainingSelector:
    def select(
            self,
            lines: list[TrainingLine],
            stats: list[LineTrainingStats],
            ) -> SelectedPath:

        children_by_parent: dict[
            UUID,
            list[TrainingLine],
        ] = defaultdict(list)

        for line in lines:
            if line.parent_id is not None:
                children_by_parent[line.parent_id].append(line)

        stats_by_key = {
            (
                item.line_id,
                item.line_analytic_version,
            ): item
            for item in stats
        }

        roots = [
            line
            for line in lines
            if line.parent_id is None
        ]

        if not roots:
            raise ValueError('Training tree has no root')

        root = roots[0]

        selected_lines = [root]
        current = root

        while True:
            children = children_by_parent.get(
                current.id,
                [],
            )

            if not children:
                break

            current = self._select_child(
                children=children,
                children_by_parent=children_by_parent,
                stats_by_key=stats_by_key,
            )

            selected_lines.append(current)

        moves: list[str] = []

        for line in selected_lines:
            moves.extend(line.moves)

        return SelectedPath(
            lines=selected_lines,
            moves=moves,
        )

    def _select_child(
            self,
            children: list[TrainingLine],
            children_by_parent: dict[
                UUID,
                list[TrainingLine],
            ],
            stats_by_key: dict[
                tuple[UUID, int],
                LineTrainingStats,
            ],
            ) -> TrainingLine:

        weights = [
            SELECTION_BASE_WEIGHT
            + SELECTION_DIFFICULTY_WEIGHT
            * self._subtree_priority(
                child,
                children_by_parent,
                stats_by_key,
            )
            for child in children
        ]

        return choices(
            children,
            weights=weights,
            k=1,
        )[0]

    def _subtree_priority(
            self,
            line: TrainingLine,
            children_by_parent: dict[
                UUID,
                list[TrainingLine],
            ],
            stats_by_key: dict[
                tuple[UUID, int],
                LineTrainingStats,
            ],
            ) -> float:

        own_priority = self._line_priority(
            line,
            stats_by_key,
        )

        children = children_by_parent.get(
            line.id,
            [],
        )

        if not children:
            return own_priority

        child_priorities = [
            self._subtree_priority(
                child,
                children_by_parent,
                stats_by_key,
            )
            for child in children
        ]

        return max(
            own_priority,
            max(child_priorities),
        )

    @staticmethod
    def _line_priority(
            line: TrainingLine,
            stats_by_key: dict[
                tuple[UUID, int],
                LineTrainingStats,
            ],
            ) -> float:

        stats = stats_by_key.get(
            (
                line.id,
                line.analytic_version,
            ),
        )

        if stats is None or stats.attempts == 0:
            return 1.0

        failure_rate = stats.fails / stats.attempts

        confidence = (
            stats.attempts
            / (
                stats.attempts
                + CONFIDENCE_ATTEMPTS
            )
        )

        return (
            confidence * failure_rate
            + (1 - confidence)
        )
