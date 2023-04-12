#include <atomic>
#include <unistd.h>
#include <thread>

struct watchdog
{
   std::atomic<int> counter;
   std::thread th;
   int usec;

   watchdog(int seconds) : th(&watchdog::watch, this), usec(seconds * 1'000'000)
   {}

   void pat()
   {
      counter++; //++ is overloaded as atomic increment
   }
   int get()
   {
      return counter.load();
   }
   void watch()
   {
      int last = get();
      while(1)
      {
         usleep(usec);
         int i = get();
         if(i == last)
            exit(-1);
         else
            last = i;
      }
   }
};

/*
int main()
{
   watchdog wd;

   while(1)
   {
      usleep(10000000);
      wd.pat();
   }

   return 0;
}
*/
