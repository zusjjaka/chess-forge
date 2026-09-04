import pytest
from pydantic import ValidationError

from schemas.line import (
    LineCreate,
    LineResponse,
    LineTreeReplace,
    LineTreeReplaceRequest,
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


class TestLineTreeReplace:
    def test_valid_leaf(self) -> None:
        data = LineTreeReplace(
            moves=['e2e4'],
        )

        assert data.moves == ['e2e4']
        assert data.children == []

    def test_children_default_to_empty_list(self) -> None:
        data = LineTreeReplace(
            moves=['e2e4'],
        )

        assert data.children == []

    def test_nested_children(self) -> None:
        data = LineTreeReplace(
            moves=['e2e4'],
            children=[
                LineTreeReplace(
                    moves=['e7e5'],
                    children=[
                        LineTreeReplace(
                            moves=['g1f3'],
                        ),
                    ],
                ),
            ],
        )

        assert len(data.children) == 1
        assert data.children[0].moves == ['e7e5']
        assert data.children[0].children[0].moves == ['g1f3']

    def test_moves_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            LineTreeReplace(
                moves=[],
            )

    def test_tag_max_length(self) -> None:
        data = LineTreeReplace(
            tag='a' * 100,
            moves=['e2e4'],
        )

        assert len(data.tag) == 100

    def test_tag_cannot_exceed_max_length(self) -> None:
        with pytest.raises(ValidationError):
            LineTreeReplace(
                tag='a' * 101,
                moves=['e2e4'],
            )


class TestLineTreeReplaceRequest:
    def test_valid_data(self) -> None:
        data = LineTreeReplaceRequest(
            version=1,
            tree=LineTreeReplace(
                moves=['e2e4'],
            ),
        )

        assert data.version == 1
        assert data.tree.moves == ['e2e4']

    def test_version_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            LineTreeReplaceRequest(
                version=0,
                tree=LineTreeReplace(
                    moves=['e2e4'],
                ),
            )

    def test_negative_version_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            LineTreeReplaceRequest(
                version=-1,
                tree=LineTreeReplace(
                    moves=['e2e4'],
                ),
            )


class TestLineResponse:
    def test_nested_response(self) -> None:
        data = LineResponse.model_validate({
            'id': '11111111-1111-1111-1111-111111111111',
            'tag': 'Root',
            'moves': ['e2e4'],
            'children': [
                {
                    'id': '22222222-2222-2222-2222-222222222222',
                    'tag': 'Reply',
                    'moves': ['e7e5'],
                    'children': [],
                },
            ],
        })

        assert data.tag == 'Root'
        assert len(data.children) == 1
        assert data.children[0].tag == 'Reply'

    def test_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError):
            LineResponse.model_validate({
                'id': 'invalid',
                'tag': None,
                'moves': ['e2e4'],
                'children': [],
            })
