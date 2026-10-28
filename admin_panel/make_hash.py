"""Generate a Werkzeug password hash for HUMAN-07 without storing the password."""

from getpass import getpass

from werkzeug.security import generate_password_hash


if __name__ == "__main__":
    password = getpass("Admin password: ")
    confirmation = getpass("Confirm password: ")
    if not password or password != confirmation:
        raise SystemExit("Passwords did not match; no hash was generated.")
    print(generate_password_hash(password))
