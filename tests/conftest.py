import pytest # type: ignore
from fastapi.testclient import TestClient # type: ignore
from unittest.mock import Mock
import libvirt # type: ignore
import logging

logger = logging.getLogger(__name__)

from src.main import app
from src.utils.libvirt_utils import get_connection_dependency

# Global test counter
test_counter = 0

def pytest_runtest_logstart(nodeid, location):
    """Log test start with sequence number"""
    global test_counter
    test_counter += 1
    test_name = location[2]  # Get the test function name
    logger.info(f"===================== Start #{test_counter} - {test_name} =====================")
            
def pytest_runtest_logfinish(nodeid, location):
    """Log test finish with sequence number"""
    global test_counter
    test_name = location[2]  # Get the test function name
    logger.info(f"===================== Finish #{test_counter} - {test_name} =====================")
            
# Ensure libvirt.VIR_DOMAIN_XML_LIVE exists for tests using mocks
if not hasattr(libvirt, "VIR_DOMAIN_XML_LIVE"):
    libvirt.VIR_DOMAIN_XML_LIVE = 1
    
@pytest.fixture(scope="session")
def client():
    """Fixture to provide a FastAPI TestClient."""
    return TestClient(app)

@pytest.fixture
def mock_libvirt_connection():
    """Fixture to provide mocked libvirt connection and domain for integration tests."""
    mock_conn = Mock(spec=libvirt.virConnect)
    mock_dom = Mock(spec=libvirt.virDomain)
    mock_conn.lookupByName.return_value = mock_dom
    # Provide a minimal valid XML for the domain
    mock_dom.XMLDesc.return_value = "<domain><devices></devices></domain>"
    return mock_conn, mock_dom

@pytest.fixture
def client_with_mocks(client, mock_libvirt_connection):
    """Fixture to provide a test client with mocked libvirt dependencies."""
    mock_conn, mock_dom = mock_libvirt_connection

    def override_get_connection():
        yield mock_conn

    app.dependency_overrides[get_connection_dependency] = override_get_connection
    yield client, mock_conn, mock_dom
    app.dependency_overrides.clear()