add_executable(tcp_test tcp_test.cpp)
target_link_libraries(tcp_test zmq czmq bfsw spdlog)
