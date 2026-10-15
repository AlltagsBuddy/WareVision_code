"""Datenbank beim Start vorbereiten (Server).

- Leere Datenbank: alle Tabellen anlegen und als aktuell markieren (alembic stamp head).
- Vorhandene Datenbank (z. B. vom PC übernommen): offene Migrationen ausführen (alembic upgrade head).
Danach Rollen prüfen (init_db).
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect  # noqa: E402

from app.core.database import engine  # noqa: E402


def main() -> None:
    tables = set(inspect(engine).get_table_names())
    backend_dir = str(Path(__file__).resolve().parent.parent)
    if "users" not in tables:
        print("Leere Datenbank: Tabellen werden angelegt.")
        subprocess.run([sys.executable, "scripts/init_db.py"], check=True, cwd=backend_dir)
        subprocess.run([sys.executable, "-m", "alembic", "stamp", "head"], check=True, cwd=backend_dir)
    else:
        print("Vorhandene Datenbank: Migrationen werden ausgeführt.")
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, cwd=backend_dir)
        subprocess.run([sys.executable, "scripts/init_db.py"], check=True, cwd=backend_dir)


if __name__ == "__main__":
    main()
