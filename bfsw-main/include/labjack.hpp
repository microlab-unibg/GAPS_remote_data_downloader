#include <stdint.h>
#include <stdlib.h>
#include <arpa/inet.h>

int labjack_query(uint8_t *qbuf, size_t qbuf_len, uint8_t *rbuf, size_t rbuf_len, const char *addr, uint16_t port);
int poll_connect(int sock, struct sockaddr_in* addr, int ms, int tries);
int poll_send(int sock, uint8_t* buf, size_t n, int ms, int tries);
int poll_recv1(int sock, uint8_t* buf, size_t n, int ms, int tries);
