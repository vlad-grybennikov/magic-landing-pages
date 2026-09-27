import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import env  # noqa: E402,F401

from pymongo import MongoClient  # noqa: E402

from migrations import migrate_pages  # noqa: E402
from settings import Settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adopt", default=None,
                        help="user id that takes ownership of ownerless pages")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    client = MongoClient(settings.mongo_url)
    report = migrate_pages(client[settings.mongo_db], adopt=args.adopt,
                           dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
