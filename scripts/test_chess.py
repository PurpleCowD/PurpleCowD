"""Exercise real move processing in an isolated copy of the profile."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class ChessFlow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ('scripts', 'assets', 'chess'):
            (self.root / folder).mkdir()
        shutil.copy(Path(__file__).with_name('chess.py'), self.root / 'scripts/chess.py')
        (self.root / 'README.md').write_text('Header\n<!-- CHESS:START -->\n<!-- CHESS:END -->\nFooter')
        self.save([])

    def save(self, moves):
        (self.root / 'chess/state.json').write_text(json.dumps({'game': 1, 'moves': [{'uci': m, 'san': m, 'player': 'tester'} for m in moves]}))

    def run_move(self, title):
        event = self.root / 'event.json'
        event.write_text(json.dumps({'issue': {'title': title, 'user': {'login': 'tester'}}}))
        return subprocess.run([sys.executable, '-P', str(self.root / 'scripts/chess.py')], env={**os.environ, 'GITHUB_EVENT_PATH': str(event)}, capture_output=True, text=True)

    def test_move_updates_board_and_preserves_profile(self):
        result = self.run_move('chess: 1:0:e2e4')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / 'README.md').read_text()
        self.assertIn('Black to move', text)
        self.assertTrue(text.startswith('Header'))
        self.assertTrue(text.endswith('Footer'))
        self.assertTrue((self.root / 'assets/chess-board.svg').exists())

    def test_illegal_stale_and_injected_commands_leave_state_unchanged(self):
        original = (self.root / 'chess/state.json').read_bytes()
        for title in ('chess: 1:0:e2e5', 'chess: 1:1:e2e4', 'chess: 1:0:new', 'chess: 1:0:e2e4; echo unsafe'):
            self.assertNotEqual(self.run_move(title).returncode, 0)
            self.assertEqual((self.root / 'chess/state.json').read_bytes(), original)

    def test_checkmate_and_new_game(self):
        self.save(['f2f3', 'e7e5', 'g2g4'])
        result = self.run_move('chess: 1:3:d8h4')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Game finished', (self.root / 'README.md').read_text())
        self.assertEqual(self.run_move('chess: 1:4:new').returncode, 0)
        self.assertEqual(json.loads((self.root / 'chess/state.json').read_text()), {'game': 2, 'moves': []})


if __name__ == '__main__':
    unittest.main()
