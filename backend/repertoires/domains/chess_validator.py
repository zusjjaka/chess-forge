import chess


class ChessValidator:
    @staticmethod
    def apply_persisted_moves(
            board: chess.Board,
            moves: list[str],
            ) -> None:
        for move in moves:
            board.push(
                chess.Move.from_uci(move),
            )

    @staticmethod
    def validate_moves(
            board: chess.Board,
            moves: list[str],
            ) -> None:
        for move in moves:
            try:
                board.push_uci(move)
            except chess.IllegalMoveError as error:
                raise ValueError(
                    f'Illegal chess move: {move}',
                ) from error
