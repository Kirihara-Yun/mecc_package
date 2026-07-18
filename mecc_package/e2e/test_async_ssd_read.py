import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
import torch
from tiered_engine import ExpertWeights, LayerExpertCache

class ControlledStore:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.release = threading.Event()
        self.submissions = []

    def load_to_cpu(self, uid, cold=True):
        return self.weights(uid)

    def weights(self, uid):
        value = float(uid[1] + 1)
        tensor = torch.full((2, 2), value)
        return ExpertWeights(tensor, tensor, tensor)

    def submit_load_to_cpu(self, uid, cold=True):
        self.submissions.append(uid)
        return self.pool.submit(self.delayed, uid)

    def delayed(self, uid):
        self.release.wait(timeout=2)
        return self.weights(uid)

class AsyncSSDReadTest(unittest.TestCase):
    def test_submission_is_nonblocking_and_access_has_completion_barrier(self):
        store = ControlledStore()
        cache = LayerExpertCache(0, store, [(0, 0), (0, 1), (0, 2)], 1, 1,
                                 torch.device("cpu"), policy="ours", cold_ssd=True)
        started = time.perf_counter()
        cache.prefetch_ssd_batch([(0, 2)], is_prefill=True)
        self.assertLess(time.perf_counter() - started, 0.2)
        result = []
        thread = threading.Thread(target=lambda: result.append(cache._access((0, 2))))
        thread.start(); time.sleep(0.03)
        self.assertTrue(thread.is_alive(), "access must wait until SSD data is ready")
        store.release.set(); thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].w1[0, 0].item(), 3.0)
        self.assertEqual(cache.hits, [0, 0, 1, 0])
        store.pool.shutdown()

    def test_competitor_does_not_submit_unused_background_reads(self):
        store = ControlledStore()
        cache = LayerExpertCache(0, store, [(0, 0), (0, 1), (0, 2)], 1, 1,
                                 torch.device("cpu"), policy="swapmoe", cold_ssd=True)
        cache.prefetch_ssd_batch([(0, 2)], is_prefill=True)
        self.assertEqual(store.submissions, [])
        store.pool.shutdown()

if __name__ == "__main__": unittest.main()
