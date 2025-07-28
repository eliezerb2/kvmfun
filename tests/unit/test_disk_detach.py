import pytest
from unittest.mock import Mock, patch
from src.services.disk_detach import _get_disk_source_path, poll_for_disk_removal, detach_disk

@patch('src.services.disk_detach.parse_domain_xml')
def test_get_disk_source_path_success(mock_parse_xml):
    """Test successful disk source path retrieval."""
    mock_dom = Mock()
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
    mock_parse_xml.return_value = mock_root
    
    result = _get_disk_source_path(mock_dom, 'vdb')
    assert result == '/path/to/disk.qcow2'

@patch('src.services.disk_detach.parse_domain_xml')
def test_get_disk_source_path_not_found(mock_parse_xml):
    """Test disk not found scenario."""
    mock_dom = Mock()
    mock_dom.name.return_value = 'test_vm'
    
    mock_root = Mock()
    mock_root.findall.return_value = []
    mock_parse_xml.return_value = mock_root
    
    from src.utils.exceptions import DiskNotFound
    with pytest.raises(DiskNotFound):
        _get_disk_source_path(mock_dom, 'vdb')

@patch('src.services.disk_detach.time.sleep')
@patch('src.services.disk_detach._get_disk_source_path')
def test_poll_for_disk_removal_success(mock_get_source, mock_sleep):
    """Test successful disk removal polling."""
    mock_dom = Mock()
    mock_dom.name.return_value = 'test_vm'
    
    from src.utils.exceptions import DiskNotFound
    mock_get_source.side_effect = DiskNotFound("Disk not found")
    
    result = poll_for_disk_removal(mock_dom, 'vdb', timeout=1)
    assert result is True

@patch('src.services.disk_detach._validate_vm_for_detach')
@patch('src.services.disk_detach._get_disk_source_path')
def test_detach_disk_basic_success(mock_get_source, mock_validate):
    """Test disk detachment succeeding with basic API."""
    mock_conn = Mock()
    mock_dom = Mock()
    mock_conn.lookupByName.return_value = mock_dom
    mock_dom.name.return_value = 'test_vm'
    
    mock_get_source.return_value = '/path/to/disk.qcow2'
    
    result = detach_disk(mock_conn, 'test_vm', 'vdb')
    assert result is True
    mock_dom.detachDevice.assert_called_once()
    mock_dom.detachDeviceFlags.assert_not_called()

@patch('src.services.disk_detach._validate_vm_for_detach')
@patch('src.services.disk_detach._get_disk_source_path')
@patch('src.services.disk_detach._create_disk_xml')
def test_detach_disk_fallback(mock_create_xml, mock_get_source, mock_validate):
    """Test disk detachment falling back to flags API."""
    mock_conn = Mock()
    mock_dom = Mock()
    mock_conn.lookupByName.return_value = mock_dom
    mock_dom.name.return_value = 'test_vm'
    
    mock_get_source.return_value = '/path/to/disk.qcow2'
    mock_create_xml.return_value = '<disk></disk>'
    
    # Make detachDevice fail to trigger fallback
    mock_dom.detachDevice.side_effect = libvirt.libvirtError('Failed to detach device')
    
    result = detach_disk(mock_conn, 'test_vm', 'vdb')
    assert result is True
    mock_dom.detachDevice.assert_called_once()
    mock_dom.detachDeviceFlags.assert_called_once()

@patch('src.services.disk_detach._validate_vm_for_detach')
@patch('src.services.disk_detach._get_disk_source_path')
@patch('src.services.disk_detach._create_disk_xml')
def test_detach_disk_all_methods_fail(mock_create_xml, mock_get_source, mock_validate):
    """Test disk detachment failing with all methods."""
    mock_conn = Mock()
    mock_dom = Mock()
    mock_conn.lookupByName.return_value = mock_dom
    mock_dom.name.return_value = 'test_vm'
    
    mock_get_source.return_value = '/path/to/disk.qcow2'
    mock_create_xml.return_value = '<disk></disk>'
    
    # Make all detachment methods fail
    mock_dom.detachDevice.side_effect = libvirt.libvirtError('Failed with basic API')
    mock_dom.detachDeviceFlags.side_effect = libvirt.libvirtError('Failed with flags API')
    
    with pytest.raises(RuntimeError):
        detach_disk(mock_conn, 'test_vm', 'vdb')