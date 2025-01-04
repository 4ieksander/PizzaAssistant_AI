import logging

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[console_handler])

def get_logger(name: str):
	return logging.getLogger(name)
