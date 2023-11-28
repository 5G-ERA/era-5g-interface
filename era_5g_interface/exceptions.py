class Era5gInterfaceException(Exception):
    """Common base for all exception that this client might raise."""

    pass


class FailedToSendData(Era5gInterfaceException):
    """Raised when the data could not be sent."""

    pass


class BackPressureException(Era5gInterfaceException):
    """Raised when sending too much data (output buffer too filled)."""

    pass


class UnknownChannelTypeUsed(Era5gInterfaceException):
    """Raised when unknown ChannelType is used."""

    pass
