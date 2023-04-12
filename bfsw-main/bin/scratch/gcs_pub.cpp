#include <czmq.h>
#include <cstdint>
#include <string>
#include <ostream>
#include<iostream>
#include <bfswutil.hpp>
class AppData
{
        public:
                zloop_t *zloop = NULL;
                zsock_t *pubsock = NULL;
                zsock_t *pairsock = NULL;
		uint64_t counter = 0;
};

int pair_callback(zloop_t *zloop, zsock_t *pairsock, void *arg);
void help(int argc, char ** argv);
int main(int argc, char ** argv)
{
	// parse input 
	help(argc,argv);
	std::string pair_addr	  = argv[1];
	std::string pub_addr      = argv[2];
	
 	// initialize packet counter
	int rc; 
        AppData d;

	// make zloop
        d.zloop = zloop_new();
        assert(d.zloop != NULL);

	//make data pub socket
	d.pubsock = zsock_new_pub(pub_addr.c_str());
	assert(d.pubsock != NULL);// why does this fail? 

	// make pair socket
	d.pairsock = zsock_new_pair("");
        assert(d.pairsock != NULL);
        rc = zsock_bind(d.pairsock,"%s",pair_addr.c_str());
        assert(rc != -1);

	// wait for data to become available, and take action by running the pair_callback function! 
	zloop_reader(d.zloop,d.pairsock,pair_callback,&d);
	zloop_start(d.zloop);

	//close sockets
	zsock_destroy(&d.pairsock);
	zsock_destroy(&d.pubsock);

	return 0;
}

int pair_callback(zloop_t *zloop, zsock_t *pairsock, void *arg)
{
        //read in data from socket
        zframe_t *frameIn = zframe_recv(pairsock);
	uint8_t *buf = zframe_data(frameIn);
	uint16_t len = zframe_size(frameIn);
		
	// establish a pointer to the AppData object defined in main
	AppData *d = (AppData*)arg;

        // define packet counter and type 
	uint8_t telem_packet_type = 201;
        uint64_t counter_201 = d->counter++;

	// create a vector with packet header info
	std::vector<uint8_t> p = bfsw::make_packet_stub(telem_packet_type, counter_201, len);
	int rc = bfsw::set_header_length_field(p, len);

	// append data received to the vector
	for (int i = 0; i < len; i++) p.push_back(buf[i]);

        //make and publish zframe
        zframe_t *frame = zframe_new(p.data(),p.size());
	zframe_send(&frame,d->pubsock,0);
//	for (int i = 0; i < len + 13; i++) std::cout << p.at(i);
//	std::cout	<< std::endl; 
        
	// close frames
	zframe_destroy(&frame);
	zframe_destroy(&frameIn);

        return 0;
}

void help(int argc,char ** argv)
{
	if(argc != 3)
	{
		printf(//"1) zeromq bind address (eg tps:///xxx.xxx.xx.xx:xxxxx)\n"
				 "2) zeromq pub address (i.e. ipc:///tmp/myaddress.ipc)\n");
		printf("this program receives gcs packets from the specified pair socket address,"
				  "adds a telemetry header with a per packet type counter, and then"
				  "publishes the full packet on a zeromq pub socket\n");
		exit(-1);
	}
		
}

