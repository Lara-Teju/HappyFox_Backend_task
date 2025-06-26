import sys
import os

# Add the src directory to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_PATH)
