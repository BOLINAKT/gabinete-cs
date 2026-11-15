# -*- coding: utf-8 -*-
"""O vigia dos dados (15/11/2026)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import vigia


class TestVigia(unittest.TestCase):
    def test_idade(self):
        agora = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        self.assertAlmostEqual(vigia.idade_h("2026-11-15T06:00:00+00:00", agora), 6.0)
        self.assertAlmostEqual(vigia.idade_h("2026-11-15T06:00:00Z", agora), 6.0)
        self.assertAlmostEqual(vigia.idade_h("2026-11-15 06:00:00", agora), 6.0)
        self.assertIsNone(vigia.idade_h(None, agora))

    def test_conferir(self):
        agora = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "novo.json").write_text(json.dumps({"lido_em": "2026-11-15T10:00:00+00:00"}), encoding="utf-8")
            (raiz / "velho.json").write_text(json.dumps({"lido_em": "2026-11-05T10:00:00+00:00"}), encoding="utf-8")
            r = vigia.conferir(["novo.json:lido_em:12", "velho.json:lido_em:12", "velho.json:lido_em:12:opcional",
                                "nao_existe.json:lido_em:12", "novo.json:outro_campo:12"], agora, raiz)
        self.assertEqual([x[3] for x in r], ["ok", "velho", "velho (opcional)", "ilegivel", "ilegivel"])


if __name__ == "__main__":
    unittest.main()
