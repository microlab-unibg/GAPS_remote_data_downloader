#pragma once
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/ip.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <spdlog/spdlog.h>
#include <string>
#include <optional>
#include <bfswutil.hpp>
#include <algorithm>

namespace bfsw
{
   class tcp_client
   {
      public:

         int sock;

         //constructor opens socket, aborts on failure
         tcp_client()
         {
            sock = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
            if(sock == -1)
            {
               spdlog::error("failed to create sock, strerr: {}", strerror(errno));
               spdlog::error("aborting");
               exit(-1);
            }
         }

         //socket opened externally and passed to constructor, will not abort
         //use make_tcp_client() factory function instead of calling this constructor directly
         tcp_client(int sock) : sock(sock)
         {}

         ~tcp_client()
         {
            shutdown(sock, SHUT_RDWR);
            close(sock);
         }

         //TODO: disallow copy constructor and copy assignment
         //problem is that if you initialize this with other, the desctructor on other will close the fd
         //although... using move, you could set other.sock to an invalid value
         //see: https://stackoverflow.com/questions/56369138/moving-an-object-with-a-file-descriptor
         //plan: delete special constructors/assignments, and define move operations

         int connect_to(std::string ip_address, int port, int timeout_ms)
         {

            struct sockaddr_in addr = {};
            addr.sin_family = AF_INET;
            addr.sin_port = htons(port);
            inet_pton(AF_INET, ip_address.c_str(), &addr.sin_addr.s_addr);

            int rc = connect(sock, (const struct sockaddr*) &addr, sizeof(struct sockaddr_in));
            if(rc == 0)
               return 0;

            if(errno == EINPROGRESS)
            {
               struct pollfd pfd = {sock, POLLOUT, 0};
               poll(&pfd, 1, timeout_ms);
               int optval;
               socklen_t optlen = sizeof(optval);
               int so = getsockopt(sock, SOL_SOCKET, SO_ERROR, &optval, &optlen);
               if(optval == 0)
               {
                  spdlog::info("tcp_client::connect(): success");
                  return 0;
               }
               else
               {
                  spdlog::warn("tcp_client::connect(): connection failed: {}",strerror(optval));
                  close(sock);
                  return -1;
               }
            }
            else
            {
               spdlog::warn("tcp_client::connect(): unexpected error from connect(): {}",strerror(errno));
               close(sock);
               return -2;
            }
         }

         int send_full(std::string msg, int timeout_ms, int tries)
         {
            int i = 0;
            struct pollfd pfd = {sock, POLLOUT, 0};
            for(int t = 0; t < tries; ++t)
            {
               int p = poll(&pfd, 1, timeout_ms);
               if(p == 1)
               {
                  if(pfd.revents != POLLOUT)
                  {
                     spdlog::warn("tcp_client::send(): unexpected flags set by poll");
                     return -1;
                  }
                  //try to send remaining data
                  ssize_t n = send(sock, msg.data() + i, msg.size() - i, 0);
                  if(n == -1)
                  {
                     spdlog::warn("tcp_client::(): send failed: {}",strerror(errno));
                     return -2;
                  }
                  i += n;
                  if(i == (int)msg.size())
                     break;
               }
               else if(p == 0)
               {
                  continue; //timeout
               }
               else
               {
                  spdlog::warn("tcp_client::send(): poll failed: {}",strerror(errno));
                  return -3;
               }
            }

            return 0;
         }

         std::pair<int, std::string> recv_any(int n)
         {
            std::string msg;
            msg.assign(n, 'x');
            ssize_t s = recv(sock, msg.data(), msg.size(), 0);

            if(s == -1)
            {
               if(errno == EAGAIN || errno == EWOULDBLOCK)
               {
                  return {0,""}; //no bytes available
               }
               else
               {
                  return {-1,""}; //actual error
               }
            }
            else
            {
               msg.resize(s,'x');
               return {0,msg}; //return received bytes
            }
         }

         struct recv_until_result
         {
            int rc {-1000};
            std::string msg;
         };

         recv_until_result recv_until2(std::string footer, double timeout)
         {
            //return recv_until_result.
            //if error or footer not found, rc < 0 and msg.size() == 0.
            //if footer found, rc points to start of first ocurrence of footer in msg
            //note that multiple occurences of footer may be present in msg.

            recv_until_result res;
            struct pollfd pfd = {sock, POLLIN, 0};
            double t_start = bfsw::timestamp_monotonic();
            int rc {-1000};
            while(1)
            {
               int p = poll(&pfd, 1, 100);
               if(p == 0) //timeout, do nothing
               {}
               else if(p == -1)
               {
                  rc = -1;
                  break;
               }
               else
               {
                  const int bufsize = 2048;
                  char buf[bufsize];
                  ssize_t n = recv(sock, buf, bufsize, 0); 
                  if(n == -1) //error
                  {
                     rc = -2;
                     break;
                  }
                  else if(n == 0) //peer closed connection
                  {
                     rc = -3;
                     break;
                  }
                  else
                  {
                     for(int i = 0; i < n; ++i)
                        res.msg.push_back(buf[i]);
                     auto it = std::search(res.msg.begin(), res.msg.end(), footer.begin(), footer.end());
                     if(it != res.msg.end())
                     {
                        rc = static_cast<int>(it - res.msg.begin());
                        break;
                     }
                  }
               }

               double t_now = bfsw::timestamp_monotonic();
               if((t_now - t_start) >= timeout)
                  break;

            }

            res.rc = rc;
            if(res.rc < 0)
               res.msg.clear();
            return res;

         }


         std::string recv_until(std::string footer, double timeout)
         {
            //recv data until 1) the footer is received 2) timeout expires

            //possibly use MSG_PEEK to only read up to footer

            //corner: received msg contains multiple footers
            //corner: received msg contains a footer but does not end in a footer

            std::string msg;
            struct pollfd pfd = {sock, POLLIN, 0};
            double t_start = bfsw::timestamp_monotonic();
            while(1)
            {
               int p = poll(&pfd, 1, 100);
               if(p == -1)
               {
                  spdlog::error("tcp_client::recv_until(): poll error: {}",strerror(errno));
                  break;
               }
               else if(p == 0)
               {
                  //timeout, do nothing
               }
               else
               {
                  //optimization: extend msg, read directly into it
                  const int bufsize = 2048;
                  char buf[bufsize];
                  ssize_t n = recv(sock, buf, bufsize, 0); 
                  if(n == -1)
                  {
                     //error
                     break;
                  }
                  else if(n == 0)
                  {
                     //peer closed connection
                     break;
                  }
                  else
                  {
                     for(int i = 0; i < n; ++i)
                        msg.push_back(buf[i]);
                     auto it = std::search(msg.begin(), msg.end(), footer.begin(), footer.end());
                     if(it != msg.end())
                        break;
                  }
               }

               double t_now = bfsw::timestamp_monotonic();
               if((t_now - t_start) >= timeout)
                  break;

            }

            return msg;

         }

         //consider using thread with blocking socket, and then timeout on thread.join
         //check number of bytes avail to read
         //basic send
         //basic recv
   };

   //make this static method of tcp_client
   std::optional<tcp_client> make_tcp_client()
   {
      int sock = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
      if(sock == -1)
      {
         spdlog::error("failed to create sock, strerr: {}", strerror(errno));
         return {};
      }
      else
      {
         return tcp_client(sock);
      }
   }
}










      

