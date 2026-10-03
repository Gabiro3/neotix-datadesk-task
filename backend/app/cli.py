from pathlib import Path

from app.db import SessionLocal
from app.seed import seed_users
from app.services.import_episodes import import_episodes


def seed() -> None:
    db = SessionLocal()
    try:
        created = seed_users(db)
        print(f"seeded {created} users")
    finally:
        db.close()


def import_csv(path: str) -> None:
    db = SessionLocal()
    try:
        result = import_episodes(db, path)
        print(
            f"imported={result.imported} updated={result.updated} skipped={result.skipped}"
        )
        for skip in result.skips:
            print(f"  row {skip.row} {skip.episode_id or '-'}: {skip.reason}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    imp = sub.add_parser("import")
    imp.add_argument("path")
    args = parser.parse_args()
    if args.cmd == "seed":
        seed()
    elif args.cmd == "import":
        import_csv(str(Path(args.path)))
