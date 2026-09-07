import uuid

import pytest
from pydantic import ValidationError

from schemas.line import (
    LineBatchCreate,
    LineBatchUpdate,
    LineCreate,
    LinePatchRequest,
    LinePatchResponse,
    LineResponse,
    LineUpdate,
)


class TestLineCreate:
    def test_valid_data(self) -> None:
        data = LineCreate(
            tag='Sicilian',
            moves=['e2e4'],
        )

        assert data.tag == 'Sicilian'
        assert data.moves == ['e2e4']

    def test_tag_is_optional(self) -> None:
        data = LineCreate(
            moves=['e2e4'],
        )

        assert data.tag is None

    def test_moves_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            LineCreate(
                moves=[],
            )

    def test_invalid_uci_move(self) -> None:
        with pytest.raises(ValidationError):
            LineCreate(
                moves=['invalid'],
            )

    @pytest.mark.parametrize(
        'move',
        [
            'e2e4',
            'g1f3',
            'e7e8q',
            'a7a8r',
            'b2c1n',
            'h7h8b',
        ],
    )
    def test_valid_uci_moves(
            self,
            move: str,
            ) -> None:
        data = LineCreate(
            moves=[move],
        )

        assert data.moves == [move]

    @pytest.mark.parametrize(
        'move',
        [
            'e9e4',
            'e2e9',
            'e2',
            'e2e',
            'e2e4x',
            'e2-e4',
            'E2E4',
            'e2e4qq',
            '',
        ],
    )
    def test_invalid_uci_moves(
            self,
            move: str,
            ) -> None:
        with pytest.raises(ValidationError):
            LineCreate(
                moves=[move],
            )

    def test_promotion_move(self) -> None:
        data = LineCreate(
            moves=['e7e8q'],
        )

        assert data.moves == ['e7e8q']

    def test_tag_max_length(self) -> None:
        data = LineCreate(
            tag='a' * 100,
            moves=['e2e4'],
        )

        assert len(data.tag) == 100

    def test_tag_cannot_exceed_max_length(self) -> None:
        with pytest.raises(ValidationError):
            LineCreate(
                tag='a' * 101,
                moves=['e2e4'],
            )

    def test_tag_whitespace_is_stripped(self) -> None:
        data = LineCreate(
            tag='  Sicilian  ',
            moves=['e2e4'],
        )

        assert data.tag == 'Sicilian'


class TestLineUpdate:
    def test_valid_data(self) -> None:
        data = LineUpdate(
            tag='Updated',
            moves=['e2e4'],
        )

        assert data.tag == 'Updated'
        assert data.moves == ['e2e4']

    def test_all_fields_are_optional(self) -> None:
        data = LineUpdate()

        assert data.model_dump(exclude_unset=True) == {}

    def test_tag_can_be_null(self) -> None:
        data = LineUpdate(
            tag=None,
        )

        assert data.tag is None

    def test_moves_can_be_null(self) -> None:
        data = LineUpdate(
            moves=None,
        )

        assert data.moves is None

    def test_moves_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            LineUpdate(
                moves=[],
            )

    def test_invalid_move(self) -> None:
        with pytest.raises(ValidationError):
            LineUpdate(
                moves=['invalid'],
            )


class TestLineBatchCreate:
    def test_valid_data(self) -> None:
        line_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        data = LineBatchCreate(
            line_id=line_id,
            parent_id=parent_id,
            tag='Sicilian',
            moves=['e7e5', 'g1f3'],
        )

        assert data.line_id == line_id
        assert data.parent_id == parent_id
        assert data.tag == 'Sicilian'
        assert data.moves == ['e7e5', 'g1f3']

    def test_parent_id_is_optional(self) -> None:
        data = LineBatchCreate(
            line_id=uuid.uuid4(),
            moves=['e2e4'],
        )

        assert data.parent_id is None

    def test_line_id_is_required(self) -> None:
        with pytest.raises(ValidationError):
            LineBatchCreate(
                moves=['e2e4'],
            )

    def test_moves_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            LineBatchCreate(
                line_id=uuid.uuid4(),
                moves=[],
            )


class TestLineBatchUpdate:
    def test_valid_data(self) -> None:
        line_id = uuid.uuid4()

        data = LineBatchUpdate(
            line_id=line_id,
            tag='Updated',
            moves=['e7e5', 'g1f3'],
        )

        assert data.line_id == line_id
        assert data.tag == 'Updated'
        assert data.moves == ['e7e5', 'g1f3']

    def test_only_tag_can_be_updated(self) -> None:
        data = LineBatchUpdate(
            line_id=uuid.uuid4(),
            tag='Updated',
        )

        assert data.moves is None

    def test_only_moves_can_be_updated(self) -> None:
        data = LineBatchUpdate(
            line_id=uuid.uuid4(),
            moves=['e7e5', 'g1f3'],
        )

        assert data.tag is None
        assert data.moves == ['e7e5', 'g1f3']

    def test_all_fields_except_line_id_are_optional(self) -> None:
        data = LineBatchUpdate(
            line_id=uuid.uuid4(),
        )

        assert data.model_dump(exclude_unset=True) == {
            'line_id': data.line_id,
        }

    def test_moves_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            LineBatchUpdate(
                line_id=uuid.uuid4(),
                moves=[],
            )


class TestLinePatchRequest:
    def test_valid_create_operation(self) -> None:
        data = LinePatchRequest(
            revision=4,
            create=[
                LineBatchCreate(
                    line_id=uuid.uuid4(),
                    parent_id=uuid.uuid4(),
                    moves=['e7e5', 'g1f3'],
                ),
            ],
        )

        assert data.revision == 4
        assert len(data.create) == 1
        assert data.update == []
        assert data.delete == []

    def test_valid_update_operation(self) -> None:
        line_id = uuid.uuid4()

        data = LinePatchRequest(
            revision=4,
            update=[
                LineBatchUpdate(
                    line_id=line_id,
                    tag='Updated',
                ),
            ],
        )

        assert data.update[0].line_id == line_id

    def test_valid_delete_operation(self) -> None:
        line_id = uuid.uuid4()

        data = LinePatchRequest(
            revision=4,
            delete=[line_id],
        )

        assert data.delete == [line_id]

    def test_all_operations_can_be_combined(self) -> None:
        create_id = uuid.uuid4()
        update_id = uuid.uuid4()
        delete_id = uuid.uuid4()

        data = LinePatchRequest(
            revision=4,
            create=[
                LineBatchCreate(
                    line_id=create_id,
                    moves=['e7e5', 'g1f3'],
                ),
            ],
            update=[
                LineBatchUpdate(
                    line_id=update_id,
                    tag='Updated',
                ),
            ],
            delete=[delete_id],
        )

        assert len(data.create) == 1
        assert len(data.update) == 1
        assert data.delete == [delete_id]

    def test_revision_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            LinePatchRequest(
                revision=0,
                update=[
                    LineBatchUpdate(
                        line_id=uuid.uuid4(),
                        tag='Updated',
                    ),
                ],
            )

    def test_negative_revision_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            LinePatchRequest(
                revision=-1,
                update=[
                    LineBatchUpdate(
                        line_id=uuid.uuid4(),
                        tag='Updated',
                    ),
                ],
            )

    def test_at_least_one_operation_is_required(self) -> None:
        with pytest.raises(ValidationError):
            LinePatchRequest(
                revision=1,
            )


class TestLinePatchResponse:
    def test_valid_response(self) -> None:
        data = LinePatchResponse(
            revision=5,
        )

        assert data.revision == 5

    def test_revision_must_be_integer(self) -> None:
        with pytest.raises(ValidationError):
            LinePatchResponse(
                revision='invalid',
            )


class TestLineResponse:
    def test_nested_response(self) -> None:
        data = LineResponse.model_validate({
            'id': '11111111-1111-1111-1111-111111111111',
            'tag': 'Root',
            'moves': ['e2e4'],
            'analytic_version': 2,
            'children': [
                {
                    'id': '22222222-2222-2222-2222-222222222222',
                    'tag': 'Reply',
                    'moves': ['e7e5'],
                    'analytic_version': 4,
                    'children': [],
                },
            ],
        })

        assert data.tag == 'Root'
        assert data.analytic_version == 2
        assert len(data.children) == 1
        assert data.children[0].tag == 'Reply'
        assert data.children[0].analytic_version == 4

    def test_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError):
            LineResponse.model_validate({
                'id': 'invalid',
                'tag': None,
                'moves': ['e2e4'],
                'analytic_version': 1,
                'children': [],
            })

    def test_analytic_version_is_required(self) -> None:
        with pytest.raises(ValidationError):
            LineResponse.model_validate({
                'id': '11111111-1111-1111-1111-111111111111',
                'tag': None,
                'moves': ['e2e4'],
                'children': [],
            })
