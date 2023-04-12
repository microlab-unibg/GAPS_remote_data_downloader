#include <czmq.h>
#include <cstdint>
#include <string>
#include <cstdio>
#include <packet.hpp>

int udp_socket1(std::string address,int port);
void help(int argc, char ** argv);

int main(int argc, char ** argv)
{
	help(argc,argv);
	std::string udp_bind_addr = argv[1];
	int udp_bind_port    = atoi(argv[2]);
	assert(udp_bind_port < (1 << 16));
	std::string pub_addr      = argv[3];
	int packet_type      = atoi(argv[4]);
	assert(packet_type < 256);
	uint64_t counter = 0;

	//make data pub socket
	zsock_t *pubsock = zsock_new_pub(pub_addr.c_str());
	assert(pubsock != NULL);

	//make UDP socket
	int sock = udp_socket1(udp_bind_addr.c_str(),udp_bind_port);
	if(sock < 0)
	{
		printf("udp_socket1 failed, returned %d\n",sock);
		return -1;
	}

	uint8_t buffer[1 << 16];
	while(1)
	{
		//receive into buffer with offset
		//ignoring peer address for now
		ssize_t len = recvfrom(sock,
				                 &buffer[c_packet_header_len],
									  sizeof(buffer) - c_packet_header_len,
									  0,
									  NULL,
									  NULL);

		//format the packet header
		packet_t p;
		packet_init(&p);
		packet_timestamp(&p);
		p.buffer = buffer;
		size_t sz = c_packet_header_len + len;
		packet_set_header(&p,packet_type,counter,sz);
		packet_make_header(&p);
		counter++;

		//make and publish zframe
		zframe_t *frame = zframe_new(buffer,sz);
		zframe_send(&frame,pubsock,0);
	}


	//close sockets
	zsock_destroy(&pubsock);

	return 0;
}

void help(int argc,char ** argv)
{
	if(argc != 5)
	{
		printf("1) UDP bind address\n"
			    "2) UDP bind port\n"
				 "3) zeromq pub address (i.e. ipc:///tmp/myaddress.ipc)\n"
				  "4) packet type integer\n");
		printf("this program receives packets on a UDP port, adds a telemetry"
				  "header with a counter and specified packet type, and then"
				  "publishes the full packet on a zeromq pub socket\n");
		exit(-1);
	}
		
}

int udp_socket1(std::string address_string, int port)
{
	//handle the case where address_string = "localhost"
	if(address_string == "localhost")
		address_string = "0.0.0.0";

	int sock = socket(AF_INET,SOCK_DGRAM,0);
	if(sock == -1)
	{
		//errno
		return -1;
	}
	//bind to address
	struct sockaddr_in address;
	memset(&address,0,sizeof(address)); //didn't do this in COSI FSW
	address.sin_family = AF_INET;
	address.sin_port   = htons(port);
	inet_pton(AF_INET,address_string.c_str(),&address.sin_addr.s_addr);
	int err = bind(sock,(struct sockaddr *) &address, sizeof(address));
	if(err == -1)
	{
		//errno
		return -2;
	}

	return sock;
}







