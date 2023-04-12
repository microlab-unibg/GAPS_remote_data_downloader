#include <czmq.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>

void printhex(uint8_t*,size_t);

bool stop = false;
void handler(int n){stop = true;}

int main(int argc,char ** argv)
{

	if(argc < 3)
	{
		printf("1) pub url 2...N) sub urls\n");
		return -1;
	}

	zsock_t *pubsock = zsock_new_pub(argv[1]);
	assert(pubsock != NULL);

	zsock_t *subsock = zsock_new_sub("","");
	assert(subsock != NULL);
	for(int i = 2; i < argc; ++i)
	{
		//int ret = zsock_connect(subsock,argv[i]);
		int ret = zsock_connect(subsock,"%s",argv[i]);
		assert(ret == 0);
	}

	signal(SIGINT,handler);
	for(;;)
	{
		zframe_t *frame = zframe_recv(subsock);
		assert(frame != NULL);
		printhex(zframe_data(frame),zframe_size(frame));
		int ret = zframe_send(&frame,pubsock,0);
		assert(ret == 0);
		if(stop)
			break;
	}

	zsock_destroy(&subsock);
	zsock_destroy(&pubsock);

	return 0;
}

void printhex(uint8_t *buf, size_t sz)
{
	printf("sz:%lu ",sz);
	if(sz >= 13)
	{
		printf("hd:%0x%0x ",buf[0],buf[1]);
		printf("ty:%u ",buf[2]);
		uint16_t counter = ((uint16_t) buf[8] << 8) | buf[7];
		printf("ct:%u ",counter);
	}
	else
		printf("bad size");
	printf("\n");
}
