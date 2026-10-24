"""Source-only regression checks for pinned Bloodborne summon header adapter."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("qt_http_adapter", HERE / "patch_http_compat.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

# Exactly the critical source spans in the pinned upstream, not a runtime mock.
PARTY = """QByteArray Party(const QHttpServerRequest& request) {
    return Bloodborne::NormalizePartyKey(request.value(PartyHeader));
}
"""
BODY = """    if (!hostPlacement.isEmpty()) {
        QHttpHeaders headers = response.headers();
        if (headers.append(HostPlacementHeader, hostPlacement)) {
            response.setHeaders(std::move(headers));
        }
    }"""
REMOVE = """                   if (result.pendingHostPlacement.isEmpty()) {
                       return response;
                   }
                   QHttpHeaders headers = response.headers();
                   if (headers.append(HostPlacementHeader, result.pendingHostPlacement)) {
                       response.setHeaders(std::move(headers));
                   }
                   return response;"""
FIXTURE = "\n".join(["#include <QHttpHeaders>", PARTY, BODY, BODY, REMOVE])


class SummonHeadersCompat(unittest.TestCase):
    def test_all_three_placement_paths_keep_header(self):
        transformed = adapter.transform_bloodborne(FIXTURE)
        self.assertEqual(transformed.count("AddPlacementHeader(response, "), 3)
        self.assertIn("response.setHeader(QByteArray(HostPlacementHeader), value)", transformed)
        self.assertIn("headers.append(HostPlacementHeader, value)", transformed)
        self.assertIn("QT_VERSION < QT_VERSION_CHECK(6, 8, 0)", transformed)
        self.assertIn("#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)\n#include <QHttpHeaders>\n#endif", transformed)
        self.assertNotIn("if (!hostPlacement.isEmpty())", transformed)
        self.assertNotIn("if (result.pendingHostPlacement.isEmpty())", transformed)

    def test_duplicate_or_changed_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "already applied"):
            adapter.transform_bloodborne(adapter.transform_bloodborne(FIXTURE))
        with self.assertRaisesRegex(ValueError, "pinned source drift"):
            adapter.transform_bloodborne(FIXTURE.replace("#include <QHttpHeaders>", ""))
        with self.assertRaisesRegex(ValueError, "expects two return-paths"):
            adapter.transform_bloodborne(FIXTURE.replace(BODY, "", 1))
        with self.assertRaisesRegex(ValueError, "summon remove placement"):
            adapter.transform_bloodborne(FIXTURE.replace(REMOVE, ""))


if __name__ == "__main__":
    unittest.main()
