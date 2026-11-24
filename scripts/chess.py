"""Community chess: only legal moves for the current board revision are accepted."""
import json
from html import escape
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import chess
import chess.svg

ROOT = Path(__file__).resolve().parents[1]
state_path = ROOT / 'chess/state.json'
state = json.loads(state_path.read_text())
board = chess.Board()
for move in state['moves']:
    board.push_uci(move['uci'])

event_path = os.environ.get('GITHUB_EVENT_PATH')
event = json.loads(Path(event_path).read_text()) if event_path else {}
issue = event.get('issue', {})
title = issue.get('title', '')
match = re.fullmatch(r'chess: (\d+):(\d+):([a-h][1-8][a-h][1-8][qrbn]?|new)', title)
if issue:
    if not match:
        raise SystemExit('Invalid chess command.')
    game, ply, command = match.groups()
    if int(game) != state['game'] or int(ply) != len(state['moves']):
        raise SystemExit('This board has changed. Choose a move from the current README.')
    if command == 'new':
        if not board.is_game_over():
            raise SystemExit('Finish the current game first.')
        state = {'game': state['game'] + 1, 'moves': []}
        board.reset()
    else:
        move = chess.Move.from_uci(command)
        if board.is_game_over() or move not in board.legal_moves:
            raise SystemExit('Illegal move.')
        san = board.san(move)
        board.push(move)
        state['moves'].append({'uci': command, 'san': san, 'player': issue['user']['login']})

repo = os.environ.get('GITHUB_REPOSITORY', 'PurpleCowD/PurpleCowD')
def link(command):
    query = urlencode({'title': f"chess: {state['game']}:{len(state['moves'])}:{command}", 'body': 'Submit this issue to play your move. The board updates automatically; refresh the profile afterwards.'})
    return f'https://github.com/{repo}/issues/new?{query}'

status = ('White' if board.turn else 'Black') + ' to move' + (' · Check!' if board.is_check() else '')
if board.is_game_over():
    status = f'Game finished · {board.result()}'
lines = ['<!-- CHESS:START -->', f'**Game {state["game"]} · {status}**', '', '<table>', '<tr>', '<td valign="top" width="60%">', '<img src="./assets/chess-board.svg" width="480" alt="Current community chess board. Legal moves are listed alongside it." />', '</td>', '<td valign="top" width="40%">', '<h3>Choose your move</h3>']
if board.is_game_over():
    lines += [f'<p><a href="{escape(link("new"), quote=True)}">Start the next game ↗</a></p>']
else:
    lines += ['<p>Select a destination, then submit the prefilled issue. Anyone with a GitHub account can play either side.</p>', '<table>', '<tr><th>From</th><th>Move</th></tr>']
    groups = {}
    for move in sorted(board.legal_moves, key=lambda m: m.uci()):
        groups.setdefault(chess.square_name(move.from_square), []).append(move)
    for origin, moves in groups.items():
        choices = ' · '.join(f'<a href="{escape(link(m.uci()), quote=True)}">{board.san(m)}</a>' for m in moves)
        lines.append(f'<tr><td>{origin}</td><td>{choices}</td></tr>')
    lines.append('</table>')
lines += ['</td>', '</tr>', '</table>', '']
if state['moves']:
    lines += ['', '<details>', '<summary>Recent moves</summary>', '', '| Move | Player |', '| :--- | :--- |']
    for move in state['moves'][-8:]:
        lines.append(f'| {move["san"]} | [{move["player"]}](https://github.com/{move["player"]}) |')
    lines += ['', '</details>']
lines += ['<!-- CHESS:END -->']
readme = ROOT / 'README.md'
text = readme.read_text(encoding='utf-8')
text, count = re.subn(r'<!-- CHESS:START -->.*?<!-- CHESS:END -->', lambda _: '\n'.join(lines), text, flags=re.S)
if count != 1:
    raise SystemExit('Expected one chess section.')
readme.write_text(text, encoding='utf-8')
state_path.write_text(json.dumps(state, indent=2) + '\n')
(ROOT / 'assets/chess-board.svg').write_text(chess.svg.board(board, size=480, colors={'square light': '#eeeed2', 'square dark': '#769656', 'margin': '#283127', 'coord light': '#eeeed2', 'coord dark': '#eeeed2'}), encoding='utf-8')
