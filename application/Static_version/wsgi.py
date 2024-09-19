import sys, os
sys.path.append('../Account_extractor/nordigen_connector/')
from app import app
import logging

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)

ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=False, ssl_context="adhoc")

