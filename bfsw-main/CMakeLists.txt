include(FetchContent)
set (CMAKE_CXX_STANDARD 17)
cmake_minimum_required (VERSION 3.22)
project(bfsw)
find_package(Threads REQUIRED)
add_compile_options(-Wall -Wextra -pedantic -Wno-unused-variable -Wno-unused-parameter)

FetchContent_Declare(
		pybind11
		GIT_REPOSITORY https://github.com/pybind/pybind11.git
		GIT_TAG v2.10.0
)
FetchContent_MakeAvailable(pybind11)

set(SPDLOG_COMPILED_LIB ON)
FetchContent_Declare(
		spdlog
		GIT_REPOSITORY https://github.com/gabime/spdlog.git
		GIT_TAG v1.10.0
)
FetchContent_MakeAvailable(spdlog)
include_directories(${spdlog_SOURCE_DIR}/include)

include_directories(include lib/include /usr/local/include)

add_subdirectory(lib)
add_subdirectory(bin)
add_subdirectory(tests)
add_subdirectory(pybfsw/bind)
