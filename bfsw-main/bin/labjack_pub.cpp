//TODO:
//- every Q timer intervals (including the first interval) configure the labjack (whatever that might be)
//- split up query into two, ain and spi. allow for a command to write/read an arbitrary spi sequence

#include <czmq.h>
#include <stdint.h>
#include "packet.hpp"
#include "labjack.hpp"

#define c_query_len 128
typedef struct
{
	int zloop_timer_id;
	zloop_t *zloop;
	zsock_t *cmdsub,*pubsock;
	uint8_t ain_query[c_query_len];
	size_t ain_query_len;
	unsigned int good_query_count,bad_query_count,timer_count;
	unsigned int query_packet_counter,stats_packet_counter;
} data_t;
void data_init(data_t* d);

int timer_callback(zloop_t *zloop,int timer_id,void *arg);
int cmd_callback(zloop_t *zloop,zsock_t *sock,void *arg);
int main(void)
{
	int rc;
	data_t d;
	data_init(&d);

	//make zloop
	d.zloop = zloop_new();
	assert(d.zloop != NULL);

	//make zloop_timer
	d.zloop_timer_id = zloop_timer(d.zloop,1000,0,timer_callback,&d); //last arg is void* 
	assert(d.zloop_timer_id != -1);

	//make cmd sub socket
	d.cmdsub = zsock_new_sub("ipc:///tmp/cmd.ipc","");
	assert(d.cmdsub != NULL);
	rc = zloop_reader(d.zloop,d.cmdsub,cmd_callback,&d);

	//make data pub socket
	d.pubsock = zsock_new_pub("ipc:///tmp/labjack_pub.ipc");
	assert(d.pubsock != NULL);

	//run the loop
	rc = zloop_start(d.zloop);
	if(rc == 0)
		printf("zloop interrupted\n");
	else
		printf("zloop canceled by handler\n");

	//close sockets
	zsock_destroy(&d.cmdsub);
	zsock_destroy(&d.pubsock);

	return 0;
}

int timer_callback(zloop_t *zloop,int timer_id,void *arg)
{
	data_t *d = (data_t*) arg;
	d->timer_count++;
	const size_t bufsize = 512;
	uint8_t buffer[bufsize];
	int rc = labjack_query(d->ain_query,
			                 d->ain_query_len,
								  &buffer[c_packet_header_len],
								  bufsize - c_packet_header_len,
								  "192.168.37.160",
								  502);
	if(rc < 0)
	{
		d->bad_query_count++;
		printf("labjack_query returned %d\n",rc);
		if(d->bad_query_count >= 32)
		{
			//printf("too many query failures, exiting...\n");
			//return -1;
		}
	}
	else
	{
		printf("good query, got %d bytes\n",rc);
		d->good_query_count++;
		packet_t p;
		packet_init(&p);
		packet_timestamp(&p);
		p.buffer = buffer;
		size_t sz = rc + c_packet_header_len;
		packet_set_header(&p,labjack_packet,d->query_packet_counter++,sz);
		packet_make_header(&p);
		//compute_checksum
		zframe_t *frame = zframe_new(p.buffer,sz);
		zframe_send(&frame,d->pubsock,0);
	}

	if((d->timer_count & 0xF) == 0)
	{
		packet_t p;
		packet_init(&p);
		packet_timestamp(&p);
		uint8_t statsbuf[128];
		p.buffer = statsbuf;
		int i = c_packet_header_len;
		statsbuf[i++] = (uint8_t)d->good_query_count;
		statsbuf[i++] = (uint8_t)d->bad_query_count;
		statsbuf[i++] = (uint8_t)d->timer_count;
		packet_set_header(&p,labjack_stats,d->stats_packet_counter++,i);
		packet_make_header(&p);
		//compute checksum
		zframe_t *frame = zframe_new(p.buffer,i);
		zframe_send(&frame,d->pubsock,0); //automatically destroys zframe after sending
	}

	return 0;
}

int cmd_callback(zloop_t *zloop,zsock_t *sock,void *arg)
{
	printf("CMD!\n");
	return 0;
}

void data_init(data_t* d)
{
	assert(d != NULL);
	memset(d,0,sizeof(data_t));

	//setup query message
	uint8_t *b = d->ain_query;
	int i = 0;
	//header
	b[i++] = 0xAB; //transaction id
	b[i++] = 0;
	b[i++] = 0; //don't care
	b[i++] = 0; //don't care
	b[i++] = 0; //len MSB?
	b[i++] = 0; //len LSB?
	b[i++] = 1; //don't care
	b[i++] = 76; //labjack MBFB command
	//frame 0: set resolution index
	b[i++] = 1; //write
	b[i++] = 0xAB; //addr
	b[i++] = 0x7F; //addr
	b[i++] = 1; //num regs
	b[i++] = 0; //data
	b[i++] = 8; //data, 8 is max resolution index, highest fidelity
	//frame 1: set adc single ended
	b[i++] = 1; //write
	b[i++] = 0xAB; //addr
	b[i++] = 0x7E; //addr
	b[i++] = 1; //num regs
	b[i++] = 0; //data
	b[i++] = 199; //data, 199 sets all AINs to single ended
	//frame 2: set range to 10 V
	b[i++] = 1; //write
	b[i++] = 0xAB; //addr
	b[i++] = 0x7C; //addr
	b[i++] = 2; //num regs
	b[i++] = 65; //data
	b[i++] = 32; //data
	b[i++] = 0; //data
	b[i++] = 0; //data, 65 32 0 0 should be 32 bit float 10.0 big endian
	//frame 3: set settling time
	b[i++] = 1; //write
	b[i++] = 0xAB; //addr
	b[i++] = 0x80; //addr
	b[i++] = 2; //num regs
	b[i++] = 0; //data
	b[i++] = 0; //data
	b[i++] = 0; //data
	b[i++] = 0; //data, all zeros for floating point 0. auto settling time (recommended in docs)
	//frame 4: read ADC channels
	b[i++] = 0; //read
	b[i++] = 0x00; //addr
	b[i++] = 0x60; //addr
	b[i++] = 160; //num regs
	//frame 5: read temperature sensor
	b[i++] = 0; //read
	b[i++] = 0xEA; //addr
	b[i++] = 0x94; //addr
	b[i++] = 2; //num regs
	//frame 6: read system timer 20  Hz
	b[i++] = 0; //read
	b[i++] = 0xF0; //addr
	b[i++] = 0x52; //addr
	b[i++] = 2; //num regs
	assert(i <= c_query_len);
	d->ain_query_len = i;
	size_t sz = i - 6;
	b[4]   = sz >> 8;
	b[5]   = sz;
	printf("ain_query is %d bytes long\n",i);
}

	/*
	//setup spi query 
	i = 0;

	uint32_t DIO = 0b1010; //set DIO1 and DIO3 to output
	uint32_t Inhibit = 0x7FFFFF - DIO;
	//frame 7: set DIO inhibit
	b[i++] = 1; //write
	b[i++] = 0x0B; //addr
	b[i++] = 0x54; //addr
	b[i++] = 2; //num regs
	b[i++] = Inhibit >> 24;
	b[i++] = Inhibit >> 16;
	b[i++] = Inhibit >>  8;
	b[i++] = Inhibit >>  0;
	//frame 8: set DIO state
	b[i++] = 1; //write
	b[i++] = 0x0A; //addr
	b[i++] = 0xF0; //addr
	b[i++] = 2; //num regs
	b[i++] = 0;
	b[i++] = 0;
	b[i++] = 0;
	b[i++] = 0;
	//frame 9: set DIO direction
	b[i++] = 1; //write
	b[i++] = 0x0B; //addr
	b[i++] = 0x22; //addr
	b[i++] = 2; //num regs
	b[i++] = DIO >> 24;
	b[i++] = DIO >> 16;
	b[i++] = DIO >>  8;
	b[i++] = DIO >>  0;
	//frame 10: SPI config
	b[i++] = 1; //write
	b[i++] = 0x13; //addr
	b[i++] = 0x88; //addr
	b[i++] = 7; //num regs
	b[i++] = 0; //5000 = 0x1388 = SPI_CS_DIONUM
	b[i++] = 0; //DIO 0
	b[i++] = 0; //5001 = 0x1389 = SPI_CLK_DIONUM
	b[i++] = 1; //DIO 1 for clock
	b[i++] = 0; //5002 = 0x138a = SPI_MISO_DIONUM
	b[i++] = 2; //DIO 2 for MISO
	b[i++] = 0; //5003 = 0x138b = SPI_MOSI_DIONUM
	b[i++] = 3; //DIO 3 for MOSI
	b[i++] = 0; //5004 = 0x138c = SPI_MODE
	b[i++] = 0; //CPOL = 0, CPHA = 0
	b[i++] = 0xFE; //5005 = 0x138d = SPI_SPEED_THROTTLE
	b[i++] = 0x4C; //0xFE4c = 65100 should be about 10 kHz clock
	b[i++] = 0; //5006 = 0x138e = SPI_OPTIONS
	b[i++] = 0b10000011; //auto-CS disabled, set DIO disabled, MSB first, 8 bits on last byte
	//frame 11: SPI set up TX
	b[i++] = 1; //write
	b[i++] = 0x13; //addr
	b[i++] = 0x91; //addr
	b[i++] = 1; //num regs
	b[i++] = 0; //data
	b[i++] = 4; //data, num bytes to Tx
	//frame 12: load TX bytes 
	*/

	/*
	//header
	mQueryMessage.push_back(0xab);
	mQueryMessage.push_back(0);
	mQueryMessage.push_back(0); //dont care
	mQueryMessage.push_back(0); //don't care
	mQueryMessage.push_back(0); //len MSB
	mQueryMessage.push_back(0); //len LSB
	mQueryMessage.push_back(1); //don't care
	mQueryMessage.push_back(76); //labjack MBFB command
	//frame 0: set resolution index
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0xab); //addr
	mQueryMessage.push_back(0x7f); //addr
	mQueryMessage.push_back(1); //num regs
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(8); //data, 8 is max resolution index, highest fidelity
	//frame 1: set adc single ended
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0xab); //addr
	mQueryMessage.push_back(0x7e); //addr
	mQueryMessage.push_back(1); //num regs
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(199); //data, 199 sets all AINs to single ended
	//frame 2: set range to 10 V
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0xab); //addr
	mQueryMessage.push_back(0x7c); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back(65); //data
	mQueryMessage.push_back(32); //data
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(0); //data   65 32 0 0 should be 32 bit float 10.0 in big endian
	//frame 3: set settling time
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0xab); //addr
	mQueryMessage.push_back(0x80); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(0); //data
	mQueryMessage.push_back(0); //data   all zeros for floating point 0 . auto settling time (recommended by labjack)
	//frame 4: read ADC channels
	mQueryMessage.push_back(0); //read
	mQueryMessage.push_back(0x00); //addr
	mQueryMessage.push_back(0x60); //addr //AIN48 - AIN127 are extended channels available with mux80
	mQueryMessage.push_back(160); //num regs
	//frame 5: read temperature sensor
	mQueryMessage.push_back(0); //read
	mQueryMessage.push_back(0xea); //addr
	mQueryMessage.push_back(0x94); //addr
	mQueryMessage.push_back(2); //num regs
	//frame 6: read system timer 20 Hz
	mQueryMessage.push_back(0); //read
	mQueryMessage.push_back(0xf0); //addr
	mQueryMessage.push_back(0x52); //addr
	mQueryMessage.push_back(2); //num regs
	uint32_t DIO = 0b1010; //set DIO1 and DIO3 to output
	uint32_t Inhibit = 0x7fffff - DIO;
	//frame 7: set DIO inhibit
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x0b); //addr
	mQueryMessage.push_back(0x54); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back((Inhibit >> 24) & 0xff);
	mQueryMessage.push_back((Inhibit >> 16) & 0xff);
	mQueryMessage.push_back((Inhibit >> 8) & 0xff);
	mQueryMessage.push_back((Inhibit >> 0) & 0xff);
	//frame 8: set DIO state
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x0a); //addr
	mQueryMessage.push_back(0xf0); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back(0);
	mQueryMessage.push_back(0);
	mQueryMessage.push_back(0);
	mQueryMessage.push_back(0);
	//frame 9: set DIO direction
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x0b); //addr
	mQueryMessage.push_back(0x22); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back((DIO >> 24) & 0xff);
	mQueryMessage.push_back((DIO >> 16) & 0xff);
	mQueryMessage.push_back((DIO >> 8) & 0xff);
	mQueryMessage.push_back((DIO >> 0) & 0xff);
	//frame 10: SPI config
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x13); //addr
	mQueryMessage.push_back(0x88); //addr
	mQueryMessage.push_back(7); //num regs
	mQueryMessage.push_back(0); // 5000 = 0x1388 = SPI_CS_DIONUM
	mQueryMessage.push_back(0); // //DIO 0
	mQueryMessage.push_back(0); // 5001 = 0x1389 = SPI_CLK_DIONUM
	mQueryMessage.push_back(1); // //DIO 1 for clock
	mQueryMessage.push_back(0); // 5002 = 0x138a = SPI_MISO_DIONUM
	mQueryMessage.push_back(2); // //DIO 2 for MISO
	mQueryMessage.push_back(0); // 5003 = 0x138b = SPI_MOSI_DIONUM
	mQueryMessage.push_back(3); // //DIO 3 for MOSI
	mQueryMessage.push_back(0); // 5004 = 0x138c = SPI_MODE
	mQueryMessage.push_back(0b00); // CPOL = 0, CPHA = 0
	mQueryMessage.push_back(0xfe); // 5005 = 0x138d = SPI_SPEED_THROTTLE
	mQueryMessage.push_back(0x4c); // 0xfe4c = 65100 should be about 10 kHz clock
	mQueryMessage.push_back(0); // 5006 = 0x138e = SPI_OPTIONS
	mQueryMessage.push_back(0b10000011); //auto-CS disabled, set DIO disabled, MSB first, 8 bits on last byte
	//frame 11: SPI setup TX
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x13); //addr
	mQueryMessage.push_back(0x91); //addr
	mQueryMessage.push_back(1); //num regs
	mQueryMessage.push_back(0); //num bytes to TX
	mQueryMessage.push_back(4); //num bytes to TX
	//frame 12: load TX bytes
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x13); //addr
	mQueryMessage.push_back(0x92); //addr
	mQueryMessage.push_back(2); //num regs
	mQueryMessage.push_back(0xde);
	mQueryMessage.push_back(0xad);
	mQueryMessage.push_back(0xbe);
	mQueryMessage.push_back(0xef); //0xdeadbeef for loopback test
	//frame 13: start SPI transaction
	mQueryMessage.push_back(1); //write
	mQueryMessage.push_back(0x13); //addr
	mQueryMessage.push_back(0x8f); //addr
	mQueryMessage.push_back(1); //num regs
	mQueryMessage.push_back(0); //
	mQueryMessage.push_back(1); //start SPI
	//frame 14: read SPI bytes
	mQueryMessage.push_back(0); //read
	mQueryMessage.push_back(0x13); //addr
	mQueryMessage.push_back(0xba); //addr
	mQueryMessage.push_back(2); //num regs
	size_t S = mQueryMessage.size() - 6;
	mQueryMessage[4] = (S >> 8) & 0xff;
	mQueryMessage[5] = S & 0xff;
	//TODO implement PDU SPI sequence
	//might need to add a sleep between SPI write and read, not sure if the SPI_GO command waits for the SPI to finish

	//define a reboot message
	mRebootMessage.push_back(0xab);
	mRebootMessage.push_back(0x90);
	mRebootMessage.push_back(0);
	mRebootMessage.push_back(0);
	mRebootMessage.push_back(0);
	mRebootMessage.push_back(0);
	mRebootMessage.push_back(1);
	mRebootMessage.push_back(16);
	mRebootMessage.push_back(0xf2);
	mRebootMessage.push_back(0x2e);
	mRebootMessage.push_back(2);
	mRebootMessage.push_back(0x4c);
	mRebootMessage.push_back(0x4a);
	mRebootMessage.push_back(0);
	mRebootMessage.push_back(0); //0x4c4a0000 waits zero milliseconds before rebooting
	*/
	
	/*
int labjack_query(zframe_t *qframe,zframe_t **rframe)
{
	//use zmq_stream socket to talk to labjack as client
	//remember to leave extra bytes at the front for packet header
	const size_t sz = 1024;
	uint8_t buffer[sz];
	size_t i = c_packet_header_len;

	zsock_t *streamsock = zsock_new_stream("");
	assert(streamsock != NULL);

	int rc = zsock_connect(streamsock,"tcp://192.168.37.160:502"); //timeout?
	if(rc)
	{
		zsock_destroy(&streamsock);
		*rframe = NULL;
		return -1;
	}

	char *identity = zsock_identity(streamsock);
	printf("identity: %s\n",identity);

	zframe_t *iframe = zframe_from((const char*)identity);
	assert(iframe != NULL);

	rc = zframe_send(&iframe,streamsock,ZFRAME_MORE + ZFRAME_REUSE);
	assert(rc);
	rc = zframe_send(&qframe,streamsock,ZFRAME_REUSE);
	assert(rc);

	bool success = false;
	for(int q = 0; q < 128; ++q)
	{
		zframe_t *iframe_ = zframe_recv(streamsock); //timeout?
		if(iframe_ == NULL)
			break;
		zframe_t *rframe_ = zframe_recv(streamsock);
		if(
		













	return 0;
}
*/
