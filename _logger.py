from loguru import logger


logger.remove()
logger.add("./logs/log_{time}.log", rotation="10 MB", retention="10 days", level="INFO")