import pytest
from unittest.mock import Mock, patch
from src.modules.disk_attach import _letters_to_int, _int_to_letters, get_next_available_virtio_dev

def test_letters_to_int():
    """Test letter to integer conversion."""
    assert _letters_to_int('a') == 0
    assert _letters_to_int('b') == 1
    assert _letters_to_int('z') == 25
    assert _letters_to_int('aa') == 26

def test_int_to_letters():
    """Test integer to letter conversion."""
    assert _int_to_letters(0) == 'a'
    assert _int_to_letters(1) == 'b'
    assert _int_to_letters(25) == 'z'
    assert _int_to_letters(26) == 'aa'

@patch('src.modules.disk_attach.ET.fromstring')
def test_get_next_available_virtio_dev(mock_fromstring):
    """Test finding next available device."""
    mock_dom = Mock()
    mock_dom.XMLDesc.return_value = '<domain></domain>'
    
    mock_root = Mock()
    mock_root.findall.return_value = []
    mock_fromstring.return_value = mock_root
    
    result = get_next_available_virtio_dev(mock_dom)
    assert result == 'vda'