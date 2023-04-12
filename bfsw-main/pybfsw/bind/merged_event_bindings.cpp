#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <event_builder.hpp>
#include <bfswutil.hpp>

namespace py = pybind11;

PYBIND11_MODULE(merged_event_bindings, m)
{
   py::class_<tracker::hit>(m, "tracker_hit")
      .def_readonly("row",&tracker::hit::row)
      .def_readonly("module",&tracker::hit::module)
      .def_readonly("channel",&tracker::hit::channel)
      .def_readonly("adc",&tracker::hit::adc)
      .def_readonly("asic_event_code",&tracker::hit::asic_event_code);

   py::class_<tracker::event>(m, "tracker_event")
      .def_readonly("layer",&tracker::event::layer)
      .def_readonly("flags1",&tracker::event::flags1)
      .def_readonly("event_id",&tracker::event::event_id)
      .def_readonly("event_time",&tracker::event::event_time)
      .def_readonly("hits",&tracker::event::hits);

   py::class_<event_builder::merged_event>(m, "merged_event")
      .def(py::init())
      .def("unpack", &event_builder::merged_event::unpack<std::vector<uint8_t>>)
      .def("unpack_str", &event_builder::merged_event::unpack_str)
      .def_readonly("event_id", &event_builder::merged_event::event_id)
      .def_readonly("flags0", &event_builder::merged_event::flags0)
      .def_readonly("tracker_events", &event_builder::merged_event::tracker_events)
      .def_readonly("tof_data", &event_builder::merged_event::tof_data);
}
