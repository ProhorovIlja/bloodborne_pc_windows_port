/* Windows-only real shadPS4 wepoll smoke, not a stub or an online game test.
 * Exactly one UDP datagram is sent on 127.0.0.1, never to an external server.
 */
#include <winsock2.h>
#include <ws2tcpip.h>
#include <wepoll.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#define CHECK(x) do { if (!(x)) { \
  fprintf(stderr, "Win64 wepoll integration failure, line %d: %s (WSA %d)\\n", \
          __LINE__, #x, WSAGetLastError()); return 1; \
} } while (0)

int main(void) {
    WSADATA data;
    CHECK(WSAStartup(MAKEWORD(2,2), &data) == 0);
    SOCKET rx = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    SOCKET tx = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    CHECK(rx != INVALID_SOCKET && tx != INVALID_SOCKET);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    CHECK(bind(rx, (const struct sockaddr *)&addr, sizeof(addr)) == 0);
    int len = (int)sizeof(addr);
    CHECK(getsockname(rx, (struct sockaddr *)&addr, &len) == 0);
    HANDLE port = epoll_create1(0);
    CHECK(port != NULL);
    struct epoll_event in = {0}, ready = {0};
    in.events = EPOLLIN;
    in.data.u64 = UINT64_C(0x517A4567);
    CHECK(epoll_ctl(port, EPOLL_CTL_ADD, rx, &in) == 0);
    CHECK(epoll_wait(port, &ready, 1, 0) == 0);
    const char msg[] = "native-p2p-loopback";
    CHECK(sendto(tx, msg, (int)(sizeof(msg)-1), 0,
                 (const struct sockaddr *)&addr, sizeof(addr)) == (int)(sizeof(msg)-1));
    CHECK(epoll_wait(port, &ready, 1, 3000) == 1);
    CHECK((ready.events & EPOLLIN) != 0 && ready.data.u64 == in.data.u64);
    char actual[sizeof(msg)] = {0};
    CHECK(recv(rx, actual, (int)sizeof(actual)-1, 0) == (int)(sizeof(msg)-1));
    CHECK(strcmp(msg, actual) == 0);
    CHECK(epoll_ctl(port, EPOLL_CTL_DEL, rx, NULL) == 0);
    CHECK(epoll_close(port) == 0);
    CHECK(closesocket(rx) == 0 && closesocket(tx) == 0);
    CHECK(WSACleanup() == 0);
    puts("Native BBSC wepoll: UDP loopback readiness, lifetime and payload PASS");
    return 0;
}
