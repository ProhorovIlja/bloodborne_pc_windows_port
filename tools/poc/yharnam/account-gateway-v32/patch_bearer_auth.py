"""V32 pinned shadNet HTTP bearer token ban handling and SQLite index."""
from pathlib import Path

WEB_AUTH = "server/src/webapi_auth.cpp"
DATABASE = "server/src/database.cpp"

def one(s, old, replacement, label):
    n=s.count(old)
    if n!=1:
        raise ValueError(f"V32 {label}: pinned upstream drift, expected 1, found {n}")
    return s.replace(old,replacement,1)

def patch_auth(s):
    if "SH-V32-BEARER-BAN" in s: raise ValueError("V32 HTTP auth already patched")
    # A bearer token from a banned account must not authorize any WebAPI
    # route. Refuse using the same uniform invalid-token error as revocation.
    return one(s,
        '    q.prepare(QStringLiteral("SELECT user_id, username FROM account WHERE token = ?"));',
        '''    // SH-V32-BEARER-BAN: keep revoked/banned tokens invalid at all
    // WebAPI endpoints, rather than relying solely on game login checks.
    q.prepare(QStringLiteral("SELECT user_id, username FROM account "
                             "WHERE token = ? AND banned = 0"));''',
        "HTTP token lookup banned status")

def patch_db(s):
    if "SH-V32-TOKEN-INDEX" in s: raise ValueError("V32 token index already patched")
    return one(s,
        '''    qInfo() << "Database migrations complete";''',
        '''    // SH-V32-TOKEN-INDEX: existing databases also receive this index.
    // Avoid full account-table scans on every HTTP Bearer request.
    // Do not make it UNIQUE: historic tokens must be inspected separately
    // before imposing new uniqueness constraints on production databases.
    if (!Exec("CREATE INDEX IF NOT EXISTS account_token_lookup ON account(token)"))
        return false;
    qInfo() << "Database migrations complete";''',
        "token index on existing/new SQLite databases")

def transform(src):
    return {WEB_AUTH:patch_auth(src[WEB_AUTH]), DATABASE:patch_db(src[DATABASE])}
