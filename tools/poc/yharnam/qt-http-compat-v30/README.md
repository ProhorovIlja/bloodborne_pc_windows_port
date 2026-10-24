# Qt HTTP API portability after real shadNet CI

The full native Qt server compile made it through 730/753 object build steps but
failed in pinned `server/src/webapi_server.cpp` against Ubuntu 24.04 Qt6.4.

Old Qt exposes void `QHttpServer::bind(QTcpServer*)` and a one-argument
`QHttpServer::setMissingHandler(MissingHandler)`, whose responder is an
rvalue reference. Qt 6.8 and newer returns bool from bind and accepts a
context plus handler with responder by nonconst reference. The original
`QHttpServerResponder::sendResponse` was added only in Qt6.5.

This pinned-source patch branches at compile-time using QT_VERSION and uses
`QHttpServerResponder::write(QJsonDocument, StatusCode::NotFound)`, supported
by both API generations. The existing JSON error body and 404 semantics
are kept. No changes to network game protocol, credentials or production.

Tests: Python source-anchor regressions and actual Linux/Qt shadnet CI.
The genuine Qt object build is the release gate; unit source checks alone
are not sufficient. The working Fornex/CLS server is untouched.
