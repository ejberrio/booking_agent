"""Las migraciones forman una sola línea: ids únicos y una sola cabeza.

Un id repetido (p. ej. copiar un id "bonito" de otra migración) rompe el arranque en Railway
("Cycle is detected in revisions") aunque las pruebas con SQLite pasen.
"""

import re
from collections import Counter
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


def test_ids_unicos_y_una_sola_cabeza():
    ids = Counter(
        m.group(1)
        for f in (ROOT / "migrations" / "versions").glob("*.py")
        if (m := re.search(r"^revision: str = '([0-9a-f]+)'", f.read_text(), re.M))
    )
    assert [i for i, n in ids.items() if n > 1] == []
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert len(script.get_heads()) == 1
