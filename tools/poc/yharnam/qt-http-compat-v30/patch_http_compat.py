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
