link_directories(/usr/local/lib)

add_executable(pubfunnel pubfunnel.cpp)
target_link_libraries(pubfunnel ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(tracker_pub tracker_pub.cpp)
target_link_libraries(tracker_pub ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(gsedb gsedb.cpp)
target_link_libraries(gsedb ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq sqlite spdlog)
add_executable(disklogger disklogger.cpp)
target_link_libraries(disklogger ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(pdu_server pdu_server.cpp)
target_link_libraries(pdu_server ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(command_server command_server.cpp)
target_link_libraries(command_server ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(cooling_server cooling_server.cpp)
target_link_libraries(cooling_server ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(stats stats.cpp)
target_link_libraries(stats ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(rx_example1 rx_example1.cpp)
target_link_libraries(rx_example1 ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)
add_executable(tracker_power_server tracker_power_server.cpp)
target_link_libraries(tracker_power_server ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq spdlog)

if(EXISTS $ENV{TOF_FSW}/build/tof/libGapsTof.so)
   set(FOUND_TOF_LIB TRUE)
endif()

if(EXISTS $ENV{TOF_FSW}/tof/dataclasses/C++/include)
   set(FOUND_TOF_INCLUDE TRUE)
endif()

if(FOUND_TOF_LIB AND FOUND_TOF_INCLUDE)
    message("-- Found TOF software, building event builder!")
    add_executable(event_builder event_builder.cpp)
    target_include_directories(event_builder PUBLIC $ENV{TOF_FSW}/tof/dataclasses/C++/include)
    target_link_libraries(event_builder ${CMAKE_THREAD_LIBS_INIT} bfsw czmq zmq $ENV{TOF_FSW}/build/tof/libGapsTof.so)
else()
    message("-- did not find TOF software! make sure that $TOF_FSW environment variable is defined and pointing to TOF repo")
endif()

