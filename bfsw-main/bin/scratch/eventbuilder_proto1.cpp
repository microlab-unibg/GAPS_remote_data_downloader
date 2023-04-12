#include<czmq.h>
#include<array>
#include<vector>
#include<string>
#include<memory>
#include<map>
#include<list>
#include<gfp.hpp>
#include<bfswutil.hpp>
#include<REventPacket.h>
#include<cstdint>

class MergedEvent
{
	public: 
		MergedEvent(uint32_t event_id)
		{
			m_creation_time = bfsw::timestamp_monotonic();
			m_event_id = event_id;
			m_tracker_counter = 0;
			m_tof_counter = 0;
		}

		int m_tracker_counter;
		int m_tof_counter;
		double m_creation_time;
		uint32_t m_event_id;
};
typedef std::shared_ptr<MergedEvent> MergedEventPtr;

struct appdata_t
{
	int counter;
	double time;
	std::list<MergedEventPtr> list;
	std::map<uint32_t,MergedEventPtr> map;
};


typedef std::shared_ptr<GfpTrackerEvent> TrackerEventPtr;

int rx_callback(zloop_t *loop, zsock_t *socket, void *arg)
{
	auto *d = static_cast<appdata_t*>(arg);
	zframe_t *frame = zframe_recv(socket);

	std::vector<uint8_t> bytes;
	for(int i = 0; i < zframe_size(frame); ++i)
		bytes.push_back(zframe_data(frame)[i]);

	if(bytes[2] == 60)
	{
		//tof packet
		bytes.erase(bytes.begin(), bytes.begin() + 13);
		REventPacket P;
		auto rc = P.deserialize(bytes);
		//printf("tof event_id: %lu\n",P.event_ctr);
		uint32_t event_id = P.event_ctr;
		MergedEventPtr merged_event;
		if(d->map.count(event_id))
		{
			merged_event = d->map[event_id];
		}
		else
		{
			merged_event = std::make_shared<MergedEvent>(event_id);
			d->map[event_id] = merged_event;
			d->list.push_back(merged_event);
		}
		merged_event->m_tof_counter++;

	}
	else if(bytes[2] == 80)
	{
		//tracker packet
		GfpTrackerPacket P;
		auto rc = P.Parse(bytes.data(),bytes.size(),0);
		for(const auto& E : P.mEvents)
		{
			//printf("tracker event_id: %lu\n",E->EventId);
			uint32_t event_id = E->EventId;
			MergedEventPtr merged_event;
			if(d->map.count(event_id))
			{
				merged_event = d->map[event_id];
			}
			else
			{
				merged_event = std::make_shared<MergedEvent>(event_id);
				d->map[event_id] = merged_event;
				d->list.push_back(merged_event);
			}
			merged_event->m_tracker_counter++;
		}
	}
	else
	{
		//ignore
	}

	return 0;
}

int timer_callback(zloop_t *loop, int timer_id, void *arg)
{

	appdata_t *d = (appdata_t*) arg;
	d->time = bfsw::timestamp_monotonic();

	for(int i = 0; i < 10000000; ++i)
	{
		if(d->list.size())
		{
			auto merged_event = d->list.front();
			if((d->time - merged_event->m_creation_time) > 10)
			{
				d->list.pop_front();
				d->map.erase(merged_event->m_event_id);
				printf("$>$  id:%lu  tof:%d  trk:%d\n", merged_event->m_event_id, merged_event->m_tof_counter, merged_event->m_tracker_counter);
			}
            else
            {
               break;
            }
		}
        else
        {
           break;
        }
	}

	return 0;
}

void help(int argc, char **argv)
{
	if(argc != 2)
	{
      printf("1) zmq pub address for incoming data stream\n");
		exit(-1);
	}
}


int main(int argc, char **argv)
{

	appdata_t d = {};

	help(argc,argv);

	//setup event loop
	zloop_t *loop = zloop_new();
	assert(loop != NULL);

	//setup timers
	int timer = zloop_timer(loop,200,0,timer_callback,&d);

	//setup tof zmq socket
	zsock_t *rx_socket = zsock_new_sub("","");
	assert(rx_socket != nullptr);
	assert(zsock_connect(rx_socket,"%s",argv[1]) == 0);
	zloop_reader(loop,rx_socket,rx_callback,&d);
    zsock_set_rcvhwm(rx_socket,0);
    int rcvhwm = zsock_rcvhwm(rx_socket);
    printf("rcvhwm = %d\n",rcvhwm);

	//start event loop
	int rc = zloop_start(loop);
	if(rc)
		printf("zloop cancelled by handler\n");
	else
		printf("zloop interrupted\n");

	zsock_destroy(&rx_socket);

	return 0;

}
