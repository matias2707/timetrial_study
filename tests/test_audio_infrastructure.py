"""Pruebas unitarias para los componentes dedicados de infraestructura de audio."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from infrastructure.audio.sound_effects import SoundEffectsPlayer
from infrastructure.audio.track_catalog import scan_audio_tracks


class TestAudioInfrastructure(unittest.TestCase):
    """Verifica el escaneo de pistas y reproductor de efectos de sonido."""

    def test_scan_audio_tracks_detects_supported_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            (dir_path / "track1.mp3").write_bytes(b"dummy")
            (dir_path / "track2.wav").write_bytes(b"dummy")
            (dir_path / "track3.m4a").write_bytes(b"dummy")
            (dir_path / "ignore.txt").write_text("ignore", encoding="utf-8")

            tracks = scan_audio_tracks(dir_path)
            filenames = [t["filename"] for t in tracks]
            self.assertEqual(len(tracks), 3)
            self.assertIn("track1.mp3", filenames)
            self.assertIn("track2.wav", filenames)
            self.assertIn("track3.m4a", filenames)
            self.assertNotIn("ignore.txt", filenames)

    def test_sound_effects_player_mute(self) -> None:
        player = SoundEffectsPlayer()
        self.assertFalse(player.is_muted)
        player.set_muted(True)
        self.assertTrue(player.is_muted)
        # play_start, play_complete y play_fail no deben fallar cuando está silenciado
        player.play_start()
        player.play_complete()
        player.play_fail()


if __name__ == "__main__":
    unittest.main()
