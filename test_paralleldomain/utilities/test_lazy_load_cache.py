import time
from sys import getsizeof
from unittest import mock
from unittest.mock import patch

from paralleldomain.utilities.lazy_load_cache import LazyLoadCache


def test_max_size():
    with patch("psutil.virtual_memory") as mocked_virtual_memory:
        mocked_virtual_memory.return_value.free = 2 * getsizeof(mock.MagicMock()) + 1
        mocked_virtual_memory.return_value.total = 5 * getsizeof(mock.MagicMock())

        cache = LazyLoadCache(max_ram_usage_factor=1.0)

        def _pop_fake():
            LazyLoadCache.popitem(cache)
            mocked_virtual_memory.return_value.free += getsizeof(mock.MagicMock())

        cache.popitem = _pop_fake
        mock1_loader = mock.MagicMock()
        mock2_loader = mock.MagicMock()
        mock3_loader = mock.MagicMock()

        cache.get_item(key="key1", loader=mock1_loader.load)
        mock1_loader.load.assert_called_once()
        mocked_virtual_memory.return_value.free -= getsizeof(mock.MagicMock())

        cache.get_item(key="key2", loader=mock2_loader.load)
        mock2_loader.load.assert_called_once()
        mocked_virtual_memory.return_value.free -= getsizeof(mock.MagicMock())
        cache.get_item(key="key1", loader=mock1_loader.load)
        mock1_loader.load.assert_called_once()
        mock2_loader.load.assert_called_once()

        cache.get_item(key="key3", loader=mock3_loader.load)
        mock3_loader.load.assert_called_once()
        mocked_virtual_memory.return_value.free -= getsizeof(mock.MagicMock())
        assert "key2" not in cache
        assert "key3" in cache
        assert "key1" in cache

        mock3_loader.load.assert_called_once()
        cache.get_item(key="key2", loader=mock2_loader.load)
        assert mock2_loader.load.call_count == 2
        mocked_virtual_memory.return_value.free -= getsizeof(mock.MagicMock())
        assert "key1" not in cache
        assert "key3" in cache
        assert "key2" in cache

        cache.get_item(key="key4", loader=mock2_loader.load)
        assert mock2_loader.load.call_count == 3
        mocked_virtual_memory.return_value.free -= getsizeof(mock.MagicMock())
        assert "key1" not in cache
        assert "key3" not in cache
        assert "key4" in cache
        assert "key2" in cache

def test_max_time():
    cache = LazyLoadCache(ttl=2)
    mock1_loader = mock.MagicMock()

    cache.get_item(key="key1", loader=mock1_loader.load)
    assert cache.currsize == getsizeof(mock.MagicMock())
    mock1_loader.load.assert_called_once()
    time.sleep(2)
    assert cache.currsize == 0


def test_delete_lock():
    cache = LazyLoadCache(ttl=2)
    mock1_loader = mock.MagicMock()
    cache.lock_prefix(prefix="key")
    cache.get_item(key="key1", loader=mock1_loader.load)
    assert cache.currsize == getsizeof(mock.MagicMock())
    mock1_loader.load.assert_called_once()
    time.sleep(2)
    assert cache.currsize == getsizeof(mock.MagicMock())
    cache.unlock_prefix(prefix="key")
    assert cache.currsize == 0


def test_delete_lock_2():
    cache = LazyLoadCache(ttl=2)
    mock1_loader = mock.MagicMock()
    cache.lock_prefix(prefix="key")
    cache.get_item(key="bb", loader=mock.MagicMock())
    cache.get_item(key="bb2", loader=mock.MagicMock())
    cache.get_item(key="key1", loader=mock1_loader.load)
    cache.get_item(key="bb3", loader=mock.MagicMock())
    time.sleep(2)
    cache.get_item(key="aa", loader=mock.MagicMock())
    assert cache.currsize == 2 * getsizeof(mock.MagicMock())
    mock1_loader.load.assert_called_once()
    time.sleep(2)
    assert cache.currsize == getsizeof(mock.MagicMock())
    cache.unlock_prefix(prefix="key")
    assert cache.currsize == 0
