"""What the rules raise: a record that does not exist, or a request they refuse."""


class NotFound(LookupError):
    """A record that does not exist. The API answers 404."""


class Refused(Exception):
    """A request the rules refuse. The API answers 409."""
