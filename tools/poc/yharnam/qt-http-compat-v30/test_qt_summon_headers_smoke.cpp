// Real Qt headers smoke test for 6.4 and 6.8+.
// The production summon source is checked by test_bloodborne_headers.py and
// by the full shadnet native CMake job. This tests the versioned Qt API itself.
#include <QtGlobal>
#include <QByteArray>
#include <QList>
#include <QHttpServerResponse>
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
#include <QHttpHeaders>
#endif
#include <utility>

constexpr auto HostPlacementHeader = "X-ShadPS4-Bloodborne-Host-Placement";

void AddPlacementHeader(QHttpServerResponse& response, const QByteArray& value) {
    if (value.isEmpty())
        return;
#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    response.setHeader(QByteArray(HostPlacementHeader), value);
#else
    QHttpHeaders headers = response.headers();
    if (headers.append(HostPlacementHeader, value))
        response.setHeaders(std::move(headers));
#endif
}

int main() {
    QHttpServerResponse response{"application/json", QByteArrayLiteral("{}"),
                                 QHttpServerResponse::StatusCode::Ok};
    AddPlacementHeader(response, QByteArrayLiteral("verified-placement"));
#if QT_VERSION < QT_VERSION_CHECK(6, 8, 0)
    const auto vals = response.headers(QByteArray(HostPlacementHeader));
    if (vals.size() != 1 || vals.first() != QByteArrayLiteral("verified-placement"))
        return 1;
#else
    if (response.headers().isEmpty())
        return 1;
#endif
    return 0;
}
