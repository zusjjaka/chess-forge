import chess
import pytest

from domains.chess_validator import ChessValidator


class TestChessValidatorApplyPersistedMoves:
    def test_applies_single_move(self) -> None:
        board = chess.Board()

        ChessValidator.apply_persisted_moves(
            board,
            ['e2e4'],
        )

        assert board.fen() == chess.Board(
            'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
        ).fen()

    def test_applies_multiple_moves(self) -> None:
        board = chess.Board()

        ChessValidator.apply_persisted_moves(
            board,
            [
                'e2e4',
                'e7e5',
                'g1f3',
            ],
        )

        assert board.piece_at(chess.F3) == chess.Piece(
            chess.KNIGHT,
            chess.WHITE,
        )
        assert board.piece_at(chess.E5) == chess.Piece(
            chess.PAWN,
            chess.BLACK,
        )

    def test_does_not_validate_legality(self) -> None:
        board = chess.Board()

        ChessValidator.apply_persisted_moves(
            board,
            ['e2e4'],
        )

        assert board.turn == chess.BLACK


class TestChessValidatorValidateMoves:
    def test_accepts_legal_move(self) -> None:
        board = chess.Board()

        ChessValidator.validate_moves(
            board,
            ['e2e4'],
        )

        assert board.piece_at(chess.E4) == chess.Piece(
            chess.PAWN,
            chess.WHITE,
        )

    def test_accepts_legal_sequence(self) -> None:
        board = chess.Board()

        ChessValidator.validate_moves(
            board,
            [
                'e2e4',
                'e7e5',
                'g1f3',
                'b8c6',
            ],
        )

        assert board.piece_at(chess.F3) == chess.Piece(
            chess.KNIGHT,
            chess.WHITE,
        )
        assert board.piece_at(chess.C6) == chess.Piece(
            chess.KNIGHT,
            chess.BLACK,
        )

    def test_rejects_illegal_move(self) -> None:
        board = chess.Board()

        with pytest.raises(
            ValueError,
            match='Illegal chess move: e2e5',
        ):
            ChessValidator.validate_moves(
                board,
                ['e2e5'],
            )

    def test_rejects_move_of_empty_square(self) -> None:
        board = chess.Board()

        with pytest.raises(
            ValueError,
            match='Illegal chess move: e3e4',
        ):
            ChessValidator.validate_moves(
                board,
                ['e3e4'],
            )

    def test_rejects_move_after_position_changes(self) -> None:
        board = chess.Board()

        with pytest.raises(
            ValueError,
            match='Illegal chess move: e2e4',
        ):
            ChessValidator.validate_moves(
                board,
                [
                    'e2e4',
                    'e2e4',
                ],
            )

    def test_board_contains_successful_moves_before_failed_move(self) -> None:
        board = chess.Board()

        with pytest.raises(
            ValueError,
            match='Illegal chess move: e2e5',
        ):
            ChessValidator.validate_moves(
                board,
                [
                    'e2e4',
                    'e2e5',
                ],
            )

        assert board.piece_at(chess.E4) == chess.Piece(
            chess.PAWN,
            chess.WHITE,
        )
