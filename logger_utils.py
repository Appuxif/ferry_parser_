import logging
import os


last_launch_log = 'last_launch.log'
last_launch_err_log = 'last_launch_err.log'
if os.path.exists(last_launch_log):
    os.remove(last_launch_log)


def get_logger(name, level):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    chFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - Line: %(lineno)d - %(message)s')
    c_handler.setFormatter(chFormatter)
    logger.addHandler(c_handler)

    f_handler = logging.FileHandler(last_launch_log, mode='a+')
    f_handler.setLevel(logging.DEBUG)
    f_handler.setFormatter(chFormatter)
    logger.addHandler(f_handler)

    f_err_handler = logging.FileHandler(last_launch_err_log, mode='a+')
    f_err_handler.setLevel(logging.ERROR)
    f_err_handler.setFormatter(chFormatter)
    logger.addHandler(f_err_handler)
    return logger
