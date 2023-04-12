#include<czmq.h>
#include<vector>
#include<string>
#include<bfswutil.hpp>
#include<cstdint>
#include<packet.hpp>

void help(int argc, char **argv)
{
	if(argc != 3)
	{
		printf("usage: tof_pubsub tof_zmq_sub_address tof_zmq_pub_address\n");
		printf("example: tof_pubsub tcp://127.0.0.1:5555 ipc:///tmp/tof_pub\n");
		exit(-1);
	}
}

struct appdata_t
{
	zsock_t *tof_pub;
	unsigned int counter;
};


int rx_callback(zloop_t *loop, zsock_t *socket, void *arg)
{
	auto *d = static_cast<appdata_t*>(arg);
	zframe_t *frame = zframe_recv(socket);
	auto frame_size = zframe_size(frame);

	if( (frame_size + 13) > (1<<16) )
	{
		printf("ERROR: Tof packet too large, frame size = %lu\n",frame_size);
		return 0;
	}
	else
	{
		std::vector<uint8_t> bytes(13,0);
		for(size_t i = 0; i < zframe_size(frame); ++i)
			bytes.push_back(zframe_data(frame)[i]);
		const uint8_t tof_packet_type = 60;
		int rc = bfsw::format_header(bytes,tof_packet_type,d->counter,(uint16_t)bytes.size());
		zframe_t *new_frame = zframe_new(bytes.data(),bytes.size());
		zframe_send(&new_frame,d->tof_pub,0);
		zframe_destroy(&frame);
		d->counter++;
	}

	zframe_destroy(&frame);
	return 0;
}

int timer_callback(zloop_t *loop, int timer_id, void *arg)
{
	appdata_t *d = (appdata_t*) arg;
	printf("d->counter = %u\n",d->counter);
	return 0;
}

int main(int argc, char **argv)
{

	appdata_t d = {};

	help(argc,argv);

	//setup event loop
	zloop_t *loop = zloop_new();
	assert(loop != nullptr);

	//setup timers
	int timer = zloop_timer(loop,2000,0,timer_callback,&d);

	//tof sub socket, receive zmq frames from tof computer
	zsock_t *tof_sub = zsock_new_sub("","");
	assert(tof_sub != nullptr);
	assert(zsock_connect(tof_sub,"%s",argv[1]) == 0);
	zloop_reader(loop,tof_sub,rx_callback,&d);

	//setup pub socket
	d.tof_pub = zsock_new_pub(argv[2]);
	assert(d.tof_pub != nullptr);

	//start event loop
	int rc = zloop_start(loop);
	if(rc)
		printf("zloop cancelled by handler\n");
	else
		printf("zloop interrupted\n");

	zsock_destroy(&tof_sub);
	zsock_destroy(&d.tof_pub);

	return 0;

}
