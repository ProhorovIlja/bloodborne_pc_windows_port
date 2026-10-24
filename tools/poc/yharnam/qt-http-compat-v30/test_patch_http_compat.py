import unittest
from patch_http_compat import transform,transform_session,transform_stats,transform_backend
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


class StatsBackendQtCompatibility(unittest.TestCase):
    STATS='''#include <QHostAddress>
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "StatsServer: QHttpServer failed to attach to listener";
        return false;
    }
    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {
            responder.sendResponse(QHttpServerResponse{"application/json", toJson(body),
                                                       QHttpServerResponder::StatusCode::NotFound});
'''
    BACKEND='''#include <QHttpHeaders>
    m_http->setMissingHandler(this, [this](const QHttpServerRequest& request,
                                           QHttpServerResponder& responder) {
        QHttpServerResponse response(reply.contentType, reply.body,
                                     static_cast<QHttpServerResponse::StatusCode>(reply.status));
        if (!reply.headers.isEmpty()) {
            QHttpHeaders headers = response.headers();
            for (const auto& [name, value] : reply.headers) {
                headers.append(name, value);
            }
            response.setHeaders(std::move(headers));
        }
        responder.sendResponse(response);
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "Backend: QHttpServer failed to attach to listener";
        return false;
    }
    const QByteArray host =
        request.headers().value(QHttpHeaders::WellKnownHeader::Host).toByteArray();
    QHostAddress local = request.localAddress();'''
    def test_stats_listener_and_404_both_versions(self):
        s=transform_stats(self.STATS)
        self.assertIn('SH-QT-STATS-PORTABLE',s)
        self.assertIn('QHttpServerResponder&& responder',s)
        self.assertIn('responder.write(QJsonDocument(body), QHttpServerResponder::StatusCode::NotFound)',s)
        self.assertIn('m_http->bind(m_tcp.get());',s)
    def test_backend_headers_preserved_on_older_qt(self):
        s=transform_backend(self.BACKEND)
        self.assertIn('SH-QT-BACKEND-PORTABLE',s)
        self.assertIn('Qt 6.4\'s HeaderList is std::initializer_list',s)
        self.assertIn('Content-Type',s)
        self.assertIn('reply.headers.at(0)',s)
        self.assertIn('reply.headers.at(1)',s)
        self.assertIn('case 0:',s)
        self.assertIn('case 1:',s)
        self.assertIn('case 2:',s)
        self.assertIn('responder.write(reply.body,',s)
        self.assertIn('Unsupported backend response',s)
        self.assertIn('request.value(QByteArrayLiteral("Host"))',s)
        self.assertIn('m_tcp ? m_tcp->serverAddress()',s)
        self.assertIn('QHostAddress(QHostAddress::AnyIPv4)',s)
        self.assertIn('response.setHeaders(std::move(headers));',s)
        self.assertIn('QHttpServerResponder&& responder',s)
        self.assertIn('QHttpServerResponder& responder',s)
    def test_backend_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'backend HTTP response headers'):
            transform_backend(self.BACKEND.replace('response.setHeaders(std::move(headers));','response.setHeader(headers);'))
    def test_backend_host_address_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'backend request Host header'):
            transform_backend(self.BACKEND.replace('request.headers().value', 'request.value'))
        with self.assertRaisesRegex(ValueError,'backend local socket address'):
            transform_backend(self.BACKEND.replace('request.localAddress()', 'request.remoteAddress()'))
    def test_backend_repeat_refused(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform_backend(transform_backend(self.BACKEND))
