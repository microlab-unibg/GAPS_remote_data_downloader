#include <czmq.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "packet.hpp"

typedef struct
{
	int zloop_timer_id;
	zloop_t *zloop;
	zsock_t *cmd,*pub,*rx;
	uint32_t timer_count;
	uint64_t num_bytes;
	uint64_t packet_counter;
	uint8_t  packet_type;
} data_t;

void data_init(data_t* d);
int timer_callback(zloop_t *zloop,int timer_id,void *arg);
int cmd_callback(zloop_t *zloop,zsock_t *sock,void *arg);
int rx_callback(zloop_t *zloop,zsock_t *sock,void *arg);
void help(int argc,char ** argv);
int main(int argc, char ** argv)
{

	help(argc,argv);

	int rc;
	data_t d;
	data_init(&d);
	d.packet_type = atoi(argv[3]);

	//make zloop
	d.zloop = zloop_new();
	assert(d.zloop != NULL);

	//make zloop_timer
	d.zloop_timer_id = zloop_timer(d.zloop,1000,0,timer_callback,&d);
	assert(d.zloop_timer_id != -1);

	//make cmd sub socket
	d.cmd = zsock_new_sub("ipc:///tmp/cmd.ipc","");
	assert(d.cmd != NULL);
	rc = zloop_reader(d.zloop,d.cmd,cmd_callback,&d);

	//make rx sub socket
	d.rx = zsock_new_sub(argv[2],"");
	assert(d.rx != NULL);
	rc = zloop_reader(d.zloop,d.rx,rx_callback,&d);

	//make data pub socket
	d.pub = zsock_new_pub(argv[1]);
	assert(d.pub != NULL);

	//run the loop
	rc = zloop_start(d.zloop);
	if(rc == 0)
		printf("zloop interrupted\n");
	else
		printf("zloop canceled by handler\n");

	//close sockets
	zsock_destroy(&d.cmd);
	zsock_destroy(&d.pub);
	zsock_destroy(&d.rx);

	return 0;
}

void data_init(data_t* d)
{
	memset(d,0,sizeof(data_t));
}

int timer_callback(zloop_t *zloop,int timer_id,void *arg)
{
	data_t *d = (data_t*) arg;
	d->timer_count++;
	printf("num_bytes=%9lu packet_counter=%9lu\n",d->num_bytes,d->packet_counter);
	return 0;
}

int cmd_callback(zloop_t *zloop,zsock_t *sock,void *arg)
{
	printf("CMD!\n");
	return 0;
}

int rx_callback(zloop_t *zloop,zsock_t *sock,void *arg)
{
	data_t *d = (data_t*) arg;
	zframe_t *iframe = zframe_recv(d->rx);
	if(iframe == NULL)
		printf("frame = NULL\n");
	else
	{
		uint8_t *data = zframe_data(iframe);
		size_t frame_size = zframe_size(iframe);
		d->num_bytes += frame_size;
		packet_t p;
		packet_init(&p);
		packet_timestamp(&p);
		uint8_t buffer[1<<16];
		size_t sz = c_packet_header_len + frame_size;
		assert(sz < (1<<16));
		p.buffer = buffer;
		packet_set_header(&p,d->packet_type,d->packet_counter,sz);
		packet_make_header(&p);
		memcpy(&p.buffer[c_packet_header_len],data,frame_size);
		zframe_t *oframe = zframe_new(p.buffer,sz);
		zframe_send(&oframe,d->pub,0);
		d->packet_counter++;
		zframe_destroy(&iframe);
	}
	return 0;
}

void help(int argc, char ** argv)
{
	if(argc != 4)
	{
		printf("1) pub url 2) sub url 3) packet type\n");
		exit(-1);
	}
}
