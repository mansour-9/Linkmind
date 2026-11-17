import logging
import time

from sqlalchemy.exc import OperationalError

from app.processing import process_one
from app.connectors import process_one as collect_one


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("company_brain.worker")
    logger.info("Waiting for Company Brain jobs")
    while True:
        try:
            if process_one():
                continue
            if collect_one():
                continue
        except OperationalError:
            logger.warning("Database connection unavailable. Retrying.")
            time.sleep(3)
            continue
        time.sleep(0.5)


if __name__ == "__main__":
    main()
