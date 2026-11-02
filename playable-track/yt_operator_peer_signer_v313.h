// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V313: opt-in Linux server runtime binding for original YT LinkServer.
// Disabled unless SHYT_P2P_EDDSA_SEED_FILE points to an owner-only
// regular binary 32-byte seed. The EdDSA key is distinct from LinkAuth
// X25519 keys; clients must INDEPENDENTLY pin the logged public half.
// This only enables SERVER grants. Direct UDP + NAT and client key-pin
// delivery are separate unfinished integration stages.
#include "bloodborne_world.h"
#include "yt_server_direct_signer_v310.h"
#include <QByteArray>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QString>
#include <array>
#include <cstdint>
#include <cstring>
#include <memory>
#ifdef __linux__
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace BloodborneCoop::SHYTHybrid::OperatorPeerSignerV313 {
namespace Signer=ServerDirectSignerV310;
namespace Grant=SignedPeerGrantV279;

struct StoredSecret {
    Grant::SecretKey key{};
    ~StoredSecret() {
        // Avoid leaving an extra recoverable copy when the service ends.
        volatile std::uint8_t* bytes=key.data();
        for (std::size_t i=0;i<key.size();++i)bytes[i]=0;
    }
};

inline bool InstallFromEnvironment(BloodborneWorld::Service& service) {
    const QString path=qEnvironmentVariable("SHYT_P2P_EDDSA_SEED_FILE");
    if (path.isEmpty())
        return false; // strict default off
#ifdef __linux__
    if (path.size()>1024 || QFileInfo(path).isSymLink() ||
        !QFileInfo(path).isFile()) {
        qWarning() << "SHYT P2P signer disabled: unsafe seed file";
        return false;
    }
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly|QIODevice::Unbuffered)) {
        qWarning() << "SHYT P2P signer disabled: seed inaccessible";
        return false;
    }
    struct stat mode{};
    if (fstat(file.handle(),&mode)!=0 || !S_ISREG(mode.st_mode) ||
        mode.st_uid!=geteuid() || mode.st_nlink!=1 ||
        (mode.st_mode & 0077)!=0 || (mode.st_mode & 0400)==0 ||
        mode.st_size!=32) {
        qWarning() << "SHYT P2P signer disabled: seed is not a private 0600 file";
        return false;
    }
    QByteArray contents=file.read(33);
    if (contents.size()!=32) {
        qWarning() << "SHYT P2P signer disabled: seed must be exactly 32 bytes";
        return false;
    }
    std::array<u8,32> seed{};
    std::memcpy(seed.data(),contents.constData(),seed.size());
    contents.fill('\0');
    if (!Grant::NonZero(seed)) return false;
    auto secret=std::make_shared<StoredSecret>();
    Grant::PubKey pub{};
    LinkMonocypher::crypto_eddsa_key_pair(
        secret->key.data(),pub.data(),seed.data());
    volatile u8* wipe=seed.data();
    for(std::size_t i=0;i<seed.size();++i)wipe[i]=0;
    if (!Grant::NonZero(pub))return false;
    // Do not publish the 64-byte private key, seed, or any game data.
    // The authority pubkey is safe to distribute in operator-owned
    // client configuration, but MUST NOT be trusted when sent by a peer.
    service.SetDirectPeerIssuer(
        [secret,pub](const BloodborneWorld::Service::DirectPairSource& src,
                     const bbcoop::DirectPeerRequest& request) {
            return Signer::Issue(src,request,secret->key,pub);
        },pub);
    const QByteArray printable(
        reinterpret_cast<const char*>(pub.data()),pub.size());
    qInfo().noquote() << "SHYT P2P signer configured; authority public key:"
                      << QString::fromLatin1(printable.toHex());
    return true;
#else
    qWarning() << "SHYT P2P signer disabled: secure seed-file check only on Linux";
    return false;
#endif
}
} // namespace BloodborneCoop::SHYTHybrid::OperatorPeerSignerV313
