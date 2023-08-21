import pytest

from src.fp_interface.main import ForwardingPlane


@pytest.fixture
def mock_socket(mocker):
    mock_socket = mocker.Mock(name="sock")
    return mock_socket


@pytest.fixture
def fp(mocker, mock_socket):
    mock_socket_lib = mocker.Mock(name="socketLib", return_value=mock_socket)
    fp = ForwardingPlane(mock_socket_lib)
    return fp


def test_fp_ping(fp, mock_socket):
    rtt = fp.ping('8.8.8.8')
    mock_socket.connect.assert_called_once_with(('8.8.8.8', 1))
    mock_socket.send.assert_called_once()
    mock_socket.recv.assert_called_once()


def test_fp_ping_no_response(fp, mock_socket):
    mock_socket.recv.side_effect = TimeoutError
    with pytest.raises(TimeoutError):
        rtt = fp.ping('169.254.255.254')
