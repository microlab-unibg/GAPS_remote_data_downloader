#include <czmq.h>
#include <cstdint>
#include <string>
#include <bfswutil.hpp>
#include <spdlog/spdlog.h>

int udp_socket1(std::string address,int port);
void help(int argc, char ** argv);
int main(int argc, char ** argv)
{
	help(argc,argv);
	std::string udp_bind_addr = argv[1];
	int udp_bind_port    = atoi(argv[2]);
	assert(udp_bind_port < (1 << 16));
	std::string pub_addr      = argv[3];
	uint64_t counter = 0;

	//make data pub socket
	zsock_t *pubsock = zsock_new_pub(pub_addr.c_str());
	assert(pubsock != NULL);

	//make UDP socket
	int sock = udp_socket1(udp_bind_addr.c_str(),udp_bind_port);
	if(sock < 0)
	{
        spdlog::error("failed to create udp socket, sock = {}", sock);
		return -1;
	}

	uint64_t counter_80 = 0;
	uint64_t counter_81 = 0;
	uint64_t counter_82 = 0;
	uint64_t counter_83 = 0;
	uint64_t counter_ff = 0;
	uint8_t buffer[4096];
	bool exit = false;
	while(1)
	{
		if(exit)
			break;

        //TODO opt, recv directly into zframe, need to know how many bytes next call to recvfrom will return
		ssize_t len = recvfrom(sock, &buffer[bfsw::header_size], sizeof(buffer) - bfsw::header_size, 0, NULL, NULL);

		//handle errors from recvfrom
		if(len == -1)
		{
			if(errno == EINTR) //ctrl-c
				exit = true;
			else
				perror("recvfrom: ");
			continue;
		}

		//check that we have a full header
		if(len < 16)
		{
            spdlog::warn("incomplete header");
			continue;
		}

		//determine daq packet type
		int tracker_packet_type = buffer[bfsw::header_size + 5];

		uint8_t telem_packet_type;
		uint64_t counter;

		//map tracker packet type to telem packet type
		//increment per packet type counter
		switch(tracker_packet_type)
		{
			case 0xF0: //event data, row 0
				telem_packet_type = 80; 
				counter = counter_80++;
				break;
			case 0xF1: //event data, row 1
				telem_packet_type = 80;
				counter = counter_80++;
				break;
			case 0xF2: //event data, row 2
				telem_packet_type = 80;
				counter = counter_80++;
				break;
			case 0xF3: //event data, row 3
				telem_packet_type = 80;
				counter = counter_80++;
				break;
			case 0xF4: //event data, row 4
				telem_packet_type = 80;
				counter = counter_80++;
				break;
			case 0xF5: //event data, row 5
				telem_packet_type = 80;
				counter = counter_80++;
				break;
			case 0x08: //counters
				telem_packet_type = 81;
				counter = counter_81++;
				break;
			case 0xFE:
				telem_packet_type = 82;
				counter = counter_82++;
				break;
			case 0xFD:
				telem_packet_type = 83;
				counter = counter_83++;
				break;
			default:
				telem_packet_type = 0xFF;
				counter = counter_ff++;
				break;
		}

        size_t sz = bfsw::header_size + len;
        bfsw::array_wrapper wrap{buffer, sz};
        int rc = bfsw::format_header(wrap, telem_packet_type, counter, sz);
        if(rc < 0)
        {
           spdlog::warn("error formatting header, rc = {}", rc);
        }
        else
        {
           zframe_t *frame = zframe_new(buffer,sz);
           zframe_send(&frame,pubsock,0);
        }
	}


	//close sockets
	close(sock);
	zsock_destroy(&pubsock);

	return 0;
}

void help(int argc,char ** argv)
{
   if(argc != 4)
   {
      fmt::print("1) UDP bind address (passing the string \"any\" will bind to all addresses)\n"
            "2) UDP bind port\n"
            "3) zeromq pub address (i.e. ipc:///tmp/myaddress.ipc)\n");
      fmt::print("this program receives tracker packets at the specified address/port,"
            "adds a telemetry header with a per packet type counter, and then"
            "publishes the full packet on a zeromq pub socket\n");
      exit(-1);
   }
}

int udp_socket1(std::string address_string, int port)
{
	//check if we should listen on all addresses
	if(address_string == "any")
		address_string = "0.0.0.0";

	int sock = socket(AF_INET,SOCK_DGRAM,0);
	if(sock == -1)
	{
		return -1;
	}
	//bind to address
	struct sockaddr_in address;
	memset(&address,0,sizeof(address));
	address.sin_family = AF_INET;
	address.sin_port   = htons(port);
	int rc = inet_pton(AF_INET,address_string.c_str(),&address.sin_addr.s_addr);
	if(rc == 0)
	{
		return -2;
	}
	int err = bind(sock,(struct sockaddr *) &address, sizeof(address));
	if(err == -1)
	{
		close(sock);
		return -3;
	}

	return sock;
}

