#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include <tuple>
#include <string>
#include <cstdint>

namespace py = pybind11;

py::list make_list_of_tuples()
{
   py::list l;
   l.append(py::make_tuple(4,5,6));
   l.append(py::make_tuple("hey",1));
   return l;
}

int process_list_of_tuples(py::list& l)
{

   for(auto item : l)
   {
      auto tup = py::make_tuple(item);
      std::cout << tup[0].cast<int>()  << " ";
   }
   std::cout << std::endl;


   /* works:
   for(auto item : l)
   {
      auto tup = item.cast<std::tuple<int,int,std::string>>(); 
      std::cout << std::get<0>(tup) << " ";
      std::cout << std::get<1>(tup) << " ";
      std::cout << std::get<2>(tup) << " ";
      std::cout << std::endl; 
   }
   */

   return 0;
}

void print_list_element(py::list& l, int i)
{
   std::cout << py::int_(l[i]) << std::endl;
   return;
}

void print_tuple_element(py::tuple& tup, int i)
{
   std::cout << tup[i].cast<int>() << std::endl;
   return;
}

void process_dict(py::dict& d)
{
   for(auto pair : d)
   {
      std::cout << "key:" << py::str(pair.first) << "  val:" << py::str(pair.second) << std::endl;
   }

   return;
}

void list_of_tuples(py::list& l)
{
   for(auto& item : l)
   {

      if(!py::isinstance<py::tuple>(item))
      {
         std::cout << "not a tuple" << std::endl;
         continue;
      }

      auto tup = item.cast<py::tuple>();

      if(py::isinstance<py::int_>(tup[0]))
         std::cout << tup[0].cast<int>() << std::endl;
      else if(py::isinstance<py::str>(tup[0]))
         std::cout << py::str(tup[0]) << std::endl;
      else
         std::cout << "unknown type" << std::endl;
   }

   return;
}

void print_bytes(py::bytes& b)
{
   for(int i = 0; i < py::len(b); ++i)
   {
      std::cout << b[py::int_(i)].cast<uint8_t>() << std::endl;
   }
   return;
}




PYBIND11_MODULE(pybfsw_tests,m)
{
	m.def("make_list_of_tuples",&make_list_of_tuples);
	m.def("process_list_of_tuples",&process_list_of_tuples);
    m.def("process_dict",&process_dict);
    m.def("print_list_element",&print_list_element);
    m.def("print_tuple_element",&print_tuple_element);
    m.def("list_of_tuples",&list_of_tuples);
    m.def("print_bytes",&print_bytes);
}

