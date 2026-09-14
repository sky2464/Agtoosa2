# WHY: Test fixture for scoped symbol identity and ambiguity resolution (DEV-041/046)

class UserService:
    # NOTE: Validates user identity per ADR-001
    def validate(self, user_id: str) -> bool:
        return len(user_id) > 0


class OrderService:
    # NOTE: Validates order identity
    def validate(self, order_id: str) -> bool:
        return len(order_id) > 0


def validate(token: str) -> bool:
    # Module-level validate
    return bool(token)


# Strings that resemble function definitions should never be parsed as AST symbols
MOCK_CODE = """
def ghost_function():
    pass
"""
