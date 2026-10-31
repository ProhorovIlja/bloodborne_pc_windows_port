import unittest
from check_upstream_abi import EXPECTED,audit,fields

MOCK = '''
#define BB_RECOMP_API_VERSION 4u
struct BbCpu;
typedef void (*RcFn)(BbCpu *cpu);
typedef struct {
    uint32_t version;
    uint64_t image_base;
    uint64_t (*step)(BbCpu *cpu);
    void (*call)(BbCpu *cpu, uint64_t target, uint64_t next);
    void (*tail)(BbCpu *cpu);
    void (*bail)(BbCpu *cpu, uint64_t entry_rsp);
    void (*trace)(uint64_t offset, const uint64_t r[16], const BbCpu *cpu);
} RcApi;
typedef struct { uint64_t offset, size, hash; RcFn fn; RcFn *direct; } RcFunction;
typedef const RcFunction *(*RcInit)(const RcApi *api, size_t *count);
'''
class PinnedABITests(unittest.TestCase):
    def test_pinned_decl_accepts_identical(self):
        self.assertEqual(audit(MOCK,MOCK),{'RcApi':True,'RcFunction':True})
    def test_prevent_wrong_function_signature(self):
        with self.assertRaisesRegex(ValueError,'ABI RcApi'):
            audit(MOCK.replace('uint64_t next','uint32_t next'),MOCK)
    def test_prevent_wrong_layout_or_module_version(self):
        with self.assertRaisesRegex(ValueError,'ABI RcFunction'):
            audit(MOCK,MOCK.replace('RcFn *direct','RcFn direct'))
        with self.assertRaisesRegex(ValueError,'version/initialization'):
            audit(MOCK,MOCK.replace('VERSION 4u','VERSION 5u'))
        with self.assertRaisesRegex(ValueError,'version/initialization'):
            audit(MOCK,MOCK.replace('(*RcInit)','(*RcStart)'))
    def test_field_order_is_part_of_abi(self):
        with self.assertRaisesRegex(ValueError,'ABI RcApi'):
            audit(MOCK.replace('uint32_t version;\n    uint64_t image_base;',
                  'uint64_t image_base;\n    uint32_t version;'), MOCK)
if __name__=='__main__': unittest.main()
