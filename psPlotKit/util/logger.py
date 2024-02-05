import logging


def define_logger(module_name, logger_name):
    _logger = logging.getLogger(module_name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "{} %(asctime)s %(levelname)s: %(message)s".format(logger_name), "%H:%M:%S"
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)
    return _logger
