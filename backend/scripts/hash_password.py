"""Generate a bcrypt hash for APP_PASSWORD_HASH.

Usage:
    python -m backend.scripts.hash_password "my-password"
"""

import sys

from backend.security import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))


if __name__ == "__main__":
    main()
