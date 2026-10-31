"""Synthetic pinned-public-prefix ABI structural tests, no private game."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name('audit_upstream_cpu_layout_v190.py')
spec=importlib.util.spec_from_file_location('layout_v190',p)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
ORIGINAL='''
typedef union { uint8_t b[32]; float f[8]; uint64_t q[4]; } BbVec;
typedef struct BbCpu {
    uint64_t r[16];
    uint64_t rip;
    uint64_t flags;
    BbVec v[16];
    uint64_t mxcsr;
} BbCpu;'''

class PinnedPrefixLayoutV190(unittest.TestCase):
    def test_synthetic_public_cpu_prefix(self):
        report=a.audit(ORIGINAL)
        self.assertEqual(report['vector_registers_offset_bytes'],144)
        self.assertFalse(report['exact_complete_BbCpu_verified'])
    def test_reorder_must_fail_closed(self):
        with self.assertRaises(a.LayoutMismatch):
            a.audit(ORIGINAL.replace('uint64_t rip;\n    uint64_t flags;','uint64_t flags;\n    uint64_t rip;'))
    def test_insertion_must_fail_closed(self):
        with self.assertRaises(a.LayoutMismatch):
            a.audit(ORIGINAL.replace('uint64_t rip;', 'uint64_t EXTRA;\n uint64_t rip;'))
    def test_vector_drift_must_fail_closed(self):
        with self.assertRaises(a.LayoutMismatch):
            a.audit(ORIGINAL.replace('uint8_t b[32]', 'uint8_t b[16]'))

if __name__=='__main__':unittest.main()
