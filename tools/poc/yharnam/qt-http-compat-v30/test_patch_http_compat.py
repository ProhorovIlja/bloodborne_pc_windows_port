import unittest
from patch_http_compat import transform,transform_session
SOURCE='''#include <QHostAddress>
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "WebApiServer: QHttpServer failed to attach to listener";
        return false;
    }
    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {
            responder.sendResponse(QHttpServerResponse{
                "application/json",
                QJsonDocument(body).toJson(QJsonDocument::Compact),
                QHttpServerResponder::StatusCode::NotFound,
            });'''
class Tests(unittest.TestCase):
    def test_both_qt_api_signatures(self):
        s=transform(SOURCE)
        self.assertIn('QT_VERSION_CHECK(6, 8, 0)',s)
        self.assertIn('m_http->bind(m_tcp.get());',s)
        self.assertIn('if (!m_http->bind(m_tcp.get()))',s)
        self.assertIn('QHttpServerResponder&& responder',s)
        self.assertIn('QHttpServerResponder& responder',s)
    def test_json_notfound_preserved(self):
        s=transform(SOURCE)
        self.assertIn('responder.write(QJsonDocument(body), QHttpServerResponder::StatusCode::NotFound)',s)
        self.assertNotIn('sendResponse',s)
    def test_source_anchor_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'portable JSON 404'):
            transform(SOURCE.replace('responder.sendResponse','responder.write'))
    def test_repeat_refused(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
if __name__=='__main__':unittest.main()


class SessionUtcCompatibility(unittest.TestCase):
    SOURCE='''#include <QTimeZone>
QString IsoUtc(qint64 ms) {
    return QDateTime::fromMSecsSinceEpoch(ms, QTimeZone::UTC).toString(Qt::ISODate);
}'''
    def test_utc_both_qt_generations(self):
        s=transform_session(self.SOURCE)
        self.assertIn('SH-QT-SESSION-UTC',s)
        self.assertIn('QT_VERSION_CHECK(6, 8, 0)',s)
        self.assertIn('fromMSecsSinceEpoch(ms, Qt::UTC)',s)
        self.assertIn('fromMSecsSinceEpoch(ms, QTimeZone::UTC)',s)
        self.assertIn('Qt::ISODate',s)
    def test_fail_closed_if_upstream_drifted(self):
        with self.assertRaisesRegex(ValueError,'session UTC timestamp overload'):
            transform_session(self.SOURCE.replace('QTimeZone::UTC','QTimeZone::utc()'))
    def test_not_double_applied(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform_session(transform_session(self.SOURCE))
