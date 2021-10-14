class Error(Exception):
    """Base error for this project"""
    pass

class OutdatedError(Error):
    pass

class UnexpectedResultError(Error):
    pass
