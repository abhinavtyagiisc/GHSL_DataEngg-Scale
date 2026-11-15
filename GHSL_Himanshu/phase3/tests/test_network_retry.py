from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from complete_project import retryable_network_failure

def test_only_failed_integration_transport_errors_retry():
    report={'status':'FAILED','stage':'integration'}
    assert retryable_network_failure(report,'requests.exceptions.ConnectionError: DNS lookup failed')
    assert retryable_network_failure(report,'requests.exceptions.ReadTimeout: server timeout')
    assert not retryable_network_failure({'status':'FAILED','stage':'districts'},'requests.exceptions.ConnectionError: unavailable')
    assert not retryable_network_failure(report,'requests.exceptions.HTTPError: 404 Not Found')
    assert not retryable_network_failure(report,'requests.exceptions.SSLError: certificate validation failed')
    assert not retryable_network_failure(report,'requests.exceptions.ConnectionError: earlier error\nValueError: output checksum mismatch')
    assert not retryable_network_failure({'status':'RUNNING','stage':'integration'},'requests.exceptions.ConnectionError: unavailable')
