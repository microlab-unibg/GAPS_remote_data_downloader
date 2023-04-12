#include<vector>
#include<ctime>
#include<cstdio>

class disk_logger
{
	public:

		disk_logger(std::vector<std::string> path_names)
		{
			for(const auto& path_name: path_names)
                path_infos.emplace_back(path_name);
			maintain();
		}

		int maintain(void)
		{
			//called once in constructor, and then meant to be called  periodically (like once every few seconds)
			//in order to ensure that path to directory is still good
			int num_good_paths = 0;
			for(auto& pi: path_infos)
			{
				FILE* f = fopen((pi.path_name + "/im_here").c_str(),"r");
				if(f != nullptr)
				{
					num_good_paths++;
					pi.path_exists = true;
					fclose(f);
				}
				else
				{
					pi.path_exists = false;
				}
			}
			return num_good_paths;
		}

		int write(uint8_t *buf, size_t len)
		{
			//largest valid packet size is 65536
			if(len > 65536)
				return -1;

			int num_good_writes = 0;
			for(auto& pi: path_infos)
			{
				if(pi.file == NULL)
				{
					if(pi.path_exists)
					{
						char filename[128];
						time_t tnow = time(NULL);
						size_t n = strftime(filename,sizeof(filename),"RAW%y%m%d_%H%M%S.bin",gmtime(&tnow));
						std::string fullpath = pi.path_name + "/" + filename;
						pi.file = fopen(fullpath.c_str(),"wb");
						pi.num_bytes = 0;
					}
				}
				if(pi.file != NULL)
				{
					//write to the file
					size_t n = fwrite(buf,1,len,pi.file);
					pi.num_bytes += n;
					if(n == len)
					{
						//normal write
						num_good_writes++;
						if(pi.num_bytes > 16000000)
						{
							fclose(pi.file);
							pi.file = NULL;
						}
					}
					else
					{
						//error
						fclose(pi.file);
						pi.file = NULL;
						pi.path_exists = false;
					}
				}
			}

			return num_good_writes;
		}

	private:
		class path_info
		{
			public:
				bool path_exists;
				std::string path_name;
				FILE* file;
				uint64_t num_bytes;
				path_info(std::string path_name) : 
                   path_exists(false), 
                   path_name(path_name), 
                   file(nullptr),
                   num_bytes(0)
				{}
		};

		std::vector<path_info> path_infos;

};
