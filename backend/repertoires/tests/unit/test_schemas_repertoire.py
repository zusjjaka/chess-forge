import pytest
from pydantic import ValidationError

from models.repertoire import RepertoireSide
from schemas.repertoire import (
    RepertoireCreate,
    RepertoireListResponse,
    RepertoireResponse,
    RepertoireUpdate,
)


class TestRepertoireCreate:
    def test_valid_data(self) -> None:
        data = RepertoireCreate(
            name='Italian Game',
            description='White repertoire',
            side=RepertoireSide.WHITE,
        )

        assert data.name == 'Italian Game'
        assert data.description == 'White repertoire'
        assert data.side == RepertoireSide.WHITE

    def test_description_defaults_to_empty_string(self) -> None:
        data = RepertoireCreate(
            name='Italian Game',
            side=RepertoireSide.WHITE,
        )

        assert data.description == ''

    def test_name_min_length(self) -> None:
        data = RepertoireCreate(
            name='a',
            side=RepertoireSide.WHITE,
        )

        assert data.name == 'a'

    def test_name_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireCreate(
                name='',
                side=RepertoireSide.WHITE,
            )

    def test_name_max_length(self) -> None:
        data = RepertoireCreate(
            name='a' * 40,
            side=RepertoireSide.WHITE,
        )

        assert len(data.name) == 40

    def test_name_cannot_exceed_max_length(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireCreate(
                name='a' * 41,
                side=RepertoireSide.WHITE,
            )

    @pytest.mark.parametrize(
        'side',
        [
            RepertoireSide.WHITE,
            RepertoireSide.BLACK,
        ],
    )
    def test_valid_sides(
            self,
            side: RepertoireSide,
            ) -> None:
        data = RepertoireCreate(
            name='Repertoire',
            side=side,
        )

        assert data.side == side

    def test_invalid_side(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireCreate(
                name='Repertoire',
                side='invalid',
            )

    def test_name_whitespace_is_stripped(self) -> None:
        data = RepertoireCreate(
            name='  Italian Game  ',
            side=RepertoireSide.WHITE,
        )

        assert data.name == 'Italian Game'

    def test_description_whitespace_is_stripped(self) -> None:
        data = RepertoireCreate(
            name='Italian Game',
            description='  White repertoire  ',
            side=RepertoireSide.WHITE,
        )

        assert data.description == 'White repertoire'


class TestRepertoireUpdate:
    def test_valid_data(self) -> None:
        data = RepertoireUpdate(
            name='New Name',
            description='New description',
        )

        assert data.name == 'New Name'
        assert data.description == 'New description'

    def test_all_fields_are_optional(self) -> None:
        data = RepertoireUpdate()

        assert data.model_dump(exclude_unset=True) == {}

    def test_name_can_be_null(self) -> None:
        data = RepertoireUpdate(
            name=None,
        )

        assert data.name is None

    def test_description_can_be_null(self) -> None:
        data = RepertoireUpdate(
            description=None,
        )

        assert data.description is None

    def test_name_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireUpdate(
                name='',
            )

    def test_name_cannot_exceed_max_length(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireUpdate(
                name='a' * 41,
            )

    def test_name_whitespace_is_stripped(self) -> None:
        data = RepertoireUpdate(
            name='  New Name  ',
        )

        assert data.name == 'New Name'


class TestRepertoireResponse:
    def test_valid_response(self) -> None:
        data = RepertoireResponse.model_validate({
            'id': '11111111-1111-1111-1111-111111111111',
            'user_id': '22222222-2222-2222-2222-222222222222',
            'name': 'Italian Game',
            'description': '',
            'side': 'white',
            'revision': 7,
            'analytic_version': 3,
            'created_at': '2026-09-04T12:00:00+00:00',
            'updated_at': '2026-09-04T12:00:00+00:00',
        })

        assert data.name == 'Italian Game'
        assert data.side == RepertoireSide.WHITE
        assert data.revision == 7
        assert data.analytic_version == 3

    def test_revision_is_required(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireResponse.model_validate({
                'id': '11111111-1111-1111-1111-111111111111',
                'user_id': '22222222-2222-2222-2222-222222222222',
                'name': 'Italian Game',
                'description': '',
                'side': 'white',
                'analytic_version': 3,
                'created_at': '2026-09-04T12:00:00+00:00',
                'updated_at': '2026-09-04T12:00:00+00:00',
            })

    def test_analytic_version_is_required(self) -> None:
        with pytest.raises(ValidationError):
            RepertoireResponse.model_validate({
                'id': '11111111-1111-1111-1111-111111111111',
                'user_id': '22222222-2222-2222-2222-222222222222',
                'name': 'Italian Game',
                'description': '',
                'side': 'white',
                'revision': 7,
                'created_at': '2026-09-04T12:00:00+00:00',
                'updated_at': '2026-09-04T12:00:00+00:00',
            })


class TestRepertoireListResponse:
    def test_valid_response(self) -> None:
        data = RepertoireListResponse.model_validate({
            'items': [],
            'page': 1,
            'pages': 1,
        })

        assert data.items == []
        assert data.page == 1
        assert data.pages == 1
