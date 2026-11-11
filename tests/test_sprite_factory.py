import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src import sprite_factory


class SpriteFactoryTests(unittest.TestCase):
    def test_action_names_group_order_and_frame_suffixes(self):
        self.assertEqual(sprite_factory.action_from_name("01_reposo"), "reposo")
        self.assertEqual(sprite_factory.action_from_name("02_caminar_02"), "caminar")
        self.assertEqual(sprite_factory.action_from_name("03_salto"), "salto")
        self.assertEqual(sprite_factory.action_from_name("04_golpe_inicio"), "golpe")
        self.assertEqual(sprite_factory.action_from_name("04_golpe_activo_01"), "golpe")
        self.assertEqual(sprite_factory.action_from_name("05_derrota"), "derrota")
        self.assertEqual(sprite_factory.action_from_name("caminar_01"), "caminar")
        self.assertEqual(sprite_factory.action_from_name("golpe_activo_01"), "golpe")
        self.assertEqual(sprite_factory.action_from_name("foto-personaje"), "foto-personaje")

    def test_finds_supported_images_and_rejects_case_insensitive_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_dir = Path(temporary_directory)
            (input_dir / "b.WEBP").touch()
            (input_dir / "a.png").touch()
            self.assertEqual(
                [path.name for path in sprite_factory.find_photos(input_dir)],
                ["a.png", "b.WEBP"],
            )
            (input_dir / "A.jpg").touch()
            with self.assertRaisesRegex(ValueError, "Duplicate image names"):
                sprite_factory.find_photos(input_dir)

    def test_cli_generates_all_documented_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            for name in ("01_reposo.png", "golpe_activo_01.png"):
                Image.new("RGB", (20, 40), "white").save(input_dir / name)
            template = root / "template.json"
            template.write_text(
                json.dumps({"fighter": {"name": "Test"}}), encoding="utf-8"
            )

            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "sprite_factory",
                        "--input",
                        str(input_dir),
                        "--output",
                        str(output_dir),
                        "--template",
                        str(template),
                    ],
                ),
                patch.object(sprite_factory, "new_session", return_value=object()),
                patch.object(
                    sprite_factory,
                    "remove",
                    return_value=Image.new("RGBA", (20, 40), "red"),
                ),
            ):
                self.assertEqual(sprite_factory.main(), 0)

            self.assertTrue((output_dir / "spritesheet.png").is_file())
            with Image.open(output_dir / "portrait.png") as portrait:
                self.assertEqual(portrait.size, (256, 256))
            config = json.loads(
                (output_dir / "fighter_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["fighter"]["name"], "Test")
            self.assertEqual(set(config["animations"]), {"reposo", "golpe"})
            hitbox = config["animations"]["golpe"][0]["hitbox"]
            self.assertGreater(hitbox["width"], 0)


if __name__ == "__main__":
    unittest.main()
