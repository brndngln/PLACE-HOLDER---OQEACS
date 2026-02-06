from handlers.user_handler import get_user


def get_user_data(user_id: int):
    """Fetch user data using an unsafe SQL query (for testing)."""
    # Hardcoded password that should be moved to environment or Vault
    password = "supersecret"
    # SQL injection via f-string; do not do this in production
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # In a real app, use parameterized queries to avoid injection
    return None