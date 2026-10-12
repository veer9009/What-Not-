"""Safe domain errors; callers must not expose underlying SQL exceptions."""


class ServiceError(Exception):
    pass


class UserNotFound(ServiceError):
    pass


class SellerNotFound(ServiceError):
    pass


class ProductNotFound(ServiceError):
    pass


class AddressNotFound(ServiceError):
    pass


class OrderNotFound(ServiceError):
    pass


class DuplicateUser(ServiceError):
    pass


class DuplicateSeller(ServiceError):
    pass


class InvalidRole(ServiceError):
    pass


class InactiveUser(ServiceError):
    pass


class OwnershipError(ServiceError):
    pass


class AddressOwnershipError(OwnershipError):
    pass


class AddressInUse(ServiceError):
    pass


class InvalidProductTransition(ServiceError):
    pass


class ProductUnavailable(ServiceError):
    pass


class InsufficientStock(ServiceError):
    pass


class InvalidOrderTransition(ServiceError):
    pass


class AmountOverflow(ServiceError):
    pass


class PersistenceConflict(ServiceError):
    pass
