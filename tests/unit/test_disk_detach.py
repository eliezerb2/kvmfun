import pytest
from unittest.mock import Mock, patch
from src.modules.disk_detach import get_disk_xml_for_target_dev, poll_for_disk_removal, detach_disk

@patch('src.modules.disk_detach.ET.fromstring')
def test_get_disk_xml_for_target_dev_success(mock_fromstring):
    """Test successful disk XML retrieval."""
    mock_dom = Mock()
    mock_dom.XMLDesc.return_value = '<domain></domain>'
    mock_dom.name.return_value = 'test_vm'
    
    # Mock disk element with target and source
    mock_disk = Mock()
    mock_target = Mock()
    mock_target.get.return_value = 'vdb'
    mock_source = Mock()
    mock_source.get.return_value = '/path/to/disk.qcow2'
    
    mock_disk.find.side_effect = lambda tag: mock_target if tag == 'target' else mock_source
    
    mock_root = Mock()
    mock_root.findall.return_value = [mock_disk]
    mock_fromstring.return_value = mock_root
    
    with patch('src.modules.disk_detach.ET.tostring', return_value='<disk></disk>'):
        result = get_disk_xml_for_target_dev(mock_dom, 'vdb')
        assert result == '<disk></disk>'

def test_get_disk_xml_for_target_dev_not_found():
    """Test disk not found scenario."""
    mock_dom = Mock()
    mock_dom.XMLDesc.return_value = '<domain></domain>'
    mock_dom.name.return_value = 'test_vm'
    
    with patch('src.modules.disk_detach.ET.fromstring') as mock_fromstring:
        mock_root = Mock()
        mock_root.findall.return_value = []
        mock_fromstring.return_value = mock_root
        
        with pytest.raises(ValueError, match="Disk with target 'vdb' not found"):
            get_disk_xml_for_target_dev(mock_dom, 'vdb')

@patch('src.modules.disk_detach.time.sleep')
@patch('src.modules.disk_detach.ET.fromstring')
def test_poll_for_disk_removal_success(mock_fromstring, mock_sleep):
    """Test successful disk removal polling."""
    mock_dom = Mock()
    mock_dom.XMLDesc.return_value = '<domain></domain>'
    mock_dom.name.return_value = 'test_vm'
    
    mock_root = Mock()
    mock_root.findall.return_value = []  # No disks found = removed
    mock_fromstring.return_value = mock_root
    
    result = poll_for_disk_removal(mock_dom, 'vdb', timeout=1)
    assert result is True