#!/usr/bin/env python3
"""Adapt pinned shadNet HTTP API to Qt 6.4 and modern Qt, without changing wire JSON."""
from pathlib import Path
PATH="server/src/webapi_server.cpp"
def one(s,old,new,name):
    count=s.count(old)
    if count!=1:
        raise ValueError(f"Qt HTTP compat {name}: pinned source drift (found {count})")
    return s.replace(old,new,1)

def transform(s):
    if "SH-QT-HTTP-COMPAT-V30" in s:
        raise ValueError("Qt HTTP compat already applied")
    s=one(s,'#include <QHostAddress>',
          '#include <QHostAddress>\n#include <QtGlobal> // SH-QT-HTTP-COMPAT-V30',
          'include')
    s=one(s,
'''    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "WebApiServer: QHttpServer failed to attach to listener";
        return false;
    }''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    // Qt 6.4-6.7: bind(QTcpServer*) returns void.
    m_http->bind(m_tcp.get());
#else
    // Qt 6.8+: bind() reports whether the already-listening socket attached.
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "WebApiServer: QHttpServer failed to attach to listener";
        return false;
    }
#endif''','bind signature')
    s=one(s,
'''    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    // Older Qt takes a single std::function with rvalue responder.
    m_http->setMissingHandler(
        [](const QHttpServerRequest& req, QHttpServerResponder&& responder) {
#else
    // Newer Qt takes a context and a handler with responder by reference.
    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {
#endif''','missing-handler signature')
    s=one(s,
'''            responder.sendResponse(QHttpServerResponse{
                "application/json",
                QJsonDocument(body).toJson(QJsonDocument::Compact),
                QHttpServerResponder::StatusCode::NotFound,
            });''',
'''            // write(QJsonDocument, status) exists since Qt 6.4 and provides
            // application/json while preserving the previous 404 JSON payload.
            responder.write(QJsonDocument(body), QHttpServerResponder::StatusCode::NotFound);''',
            'portable JSON 404')
    return s


SESSION_PATH = "server/src/webapi_routes_session.cpp"

def transform_session(s):
    """Keep UTC invitation timestamps on Qt6.4 and Qt6.8+."""
    if "SH-QT-SESSION-UTC" in s:
        raise ValueError("Qt UTC compatibility already applied")
    s = one(s,
        '#include <QTimeZone>',
        '#include <QTimeZone>\n#include <QtGlobal> // SH-QT-SESSION-UTC',
        'session Qt version include')
    s = one(s,
        '    return QDateTime::fromMSecsSinceEpoch(ms, QTimeZone::UTC).toString(Qt::ISODate);',
        '''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    // Qt 6.4: QTimeZone::UTC does not exist; Qt::UTC yields the same Z timestamp.
    return QDateTime::fromMSecsSinceEpoch(ms, Qt::UTC).toString(Qt::ISODate);
#else
    return QDateTime::fromMSecsSinceEpoch(ms, QTimeZone::UTC).toString(Qt::ISODate);
#endif''',
        'session UTC timestamp overload')
    return s


STATS_PATH = "server/src/stats_server.cpp"
BACKEND_PATH = "server/src/bloodborne_backend_server.cpp"

def transform_stats(s):
    """Qt6.4/6.8+ stats HTTP listener and 404 JSON handlers."""
    if "SH-QT-STATS-PORTABLE" in s:
        raise ValueError("Qt stats compatibility already applied")
    s = one(s, '#include <QHostAddress>',
        '#include <QHostAddress>\n#include <QtGlobal> // SH-QT-STATS-PORTABLE',
        'stats Qt version include')
    s = one(s,
'''    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "StatsServer: QHttpServer failed to attach to listener";
        return false;
    }''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    m_http->bind(m_tcp.get()); // Qt 6.4 returns void
#else
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "StatsServer: QHttpServer failed to attach to listener";
        return false;
    }
#endif''', 'stats HTTP binding')
    s = one(s,
'''    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    m_http->setMissingHandler(
        [](const QHttpServerRequest& req, QHttpServerResponder&& responder) {
#else
    m_http->setMissingHandler(
        this, [](const QHttpServerRequest& req, QHttpServerResponder& responder) {
#endif''', 'stats missing-handler')
    s = one(s,
'''            responder.sendResponse(QHttpServerResponse{"application/json", toJson(body),
                                                       QHttpServerResponder::StatusCode::NotFound});''',
'''            responder.write(QJsonDocument(body), QHttpServerResponder::StatusCode::NotFound);''',
'stats 404 JSON')
    return s


def transform_backend(s):
    """Preserve backend MIME, status and custom headers on both Qt generations."""
    if "SH-QT-BACKEND-PORTABLE" in s:
        raise ValueError("Qt backend compatibility already applied")
    s = one(s, '#include <QHttpHeaders>',
'''#include <QtGlobal> // SH-QT-BACKEND-PORTABLE
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
#include <QHttpHeaders>
#endif''', 'backend headers include')
    s = one(s,
'''    m_http->setMissingHandler(this, [this](const QHttpServerRequest& request,
                                           QHttpServerResponder& responder) {''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    m_http->setMissingHandler([this](const QHttpServerRequest& request,
                                     QHttpServerResponder&& responder) {
#else
    m_http->setMissingHandler(this, [this](const QHttpServerRequest& request,
                                           QHttpServerResponder& responder) {
#endif''', 'backend missing-handler')
    s = one(s,
'''        QHttpServerResponse response(reply.contentType, reply.body,
                                     static_cast<QHttpServerResponse::StatusCode>(reply.status));
        if (!reply.headers.isEmpty()) {
            QHttpHeaders headers = response.headers();
            for (const auto& [name, value] : reply.headers) {
                headers.append(name, value);
            }
            response.setHeaders(std::move(headers));
        }
        responder.sendResponse(response);''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
        // Qt 6.4 has no QHttpHeaders/setHeaders, but supports HeaderList.
        // Preserve Content-Type, status and every backend-defined header.
        QHttpServerResponder::HeaderList headers;
        headers.append({QByteArrayLiteral("Content-Type"), reply.contentType});
        for (const auto& [name, value] : reply.headers)
            headers.append({name, value});
        responder.write(reply.body, headers,
                        static_cast<QHttpServerResponder::StatusCode>(reply.status));
#else
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
#endif''', 'backend HTTP response headers')
    s = one(s,
'''    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "Backend: QHttpServer failed to attach to listener";
        return false;
    }''',
'''#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    m_http->bind(m_tcp.get()); // Qt 6.4 returns void
#else
    if (!m_http->bind(m_tcp.get())) {
        qCritical() << "Backend: QHttpServer failed to attach to listener";
        return false;
    }
#endif''', 'backend HTTP binding')
    return s


BLOODBORNE_ROUTES_PATH = "server/src/webapi_routes_bloodborne.cpp"

def transform_bloodborne(s):
    """Preserve summon placement headers on Qt 6.4-6.7 and Qt 6.8+.

    Qt 6.4 QHttpServerResponse has setHeader(), but not QHttpHeaders /
    response.headers() / response.setHeaders(). Do not discard this header:
    older PS4/BBSC-compatible cross-area placements rely on it.
    """
    if "SH-QT-BLOODBORNE-PLACEMENT" in s:
        raise ValueError("Qt Bloodborne header compatibility already applied")
    s = one(s, "#include <QHttpHeaders>",
        """#include <QtGlobal> // SH-QT-BLOODBORNE-PLACEMENT
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
#include <QHttpHeaders>
#endif""", "summon Qt header include")
    after_party = """QByteArray Party(const QHttpServerRequest& request) {
    return Bloodborne::NormalizePartyKey(request.value(PartyHeader));
}
"""
    with_helper = after_party + """
void AddPlacementHeader(QHttpServerResponse& response, const QByteArray& value) {
    if (value.isEmpty())
        return;
#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    // Qt 6.4-6.7 exposes setHeader(), not QHttpHeaders.
    response.setHeader(QByteArray(HostPlacementHeader), value);
#else
    QHttpHeaders headers = response.headers();
    if (headers.append(HostPlacementHeader, value))
        response.setHeaders(std::move(headers));
#endif
}
"""
    s = one(s, after_party, with_helper, "summon helper")
    two_responses = """    if (!hostPlacement.isEmpty()) {
        QHttpHeaders headers = response.headers();
        if (headers.append(HostPlacementHeader, hostPlacement)) {
            response.setHeaders(std::move(headers));
        }
    }"""
    if s.count(two_responses) != 2:
        raise ValueError("Qt summon helper expects two return-paths")
    s = s.replace(two_responses, "    AddPlacementHeader(response, hostPlacement);", 2)
    delete_response = """                   if (result.pendingHostPlacement.isEmpty()) {
                       return response;
                   }
                   QHttpHeaders headers = response.headers();
                   if (headers.append(HostPlacementHeader, result.pendingHostPlacement)) {
                       response.setHeaders(std::move(headers));
                   }
                   return response;"""
    s = one(s, delete_response,
        """                   AddPlacementHeader(response, result.pendingHostPlacement);
                   return response;""", "summon remove placement")
    if s.count("AddPlacementHeader(response, ") != 3:
        raise ValueError("Qt summon compat lost a placement path")
    return s
