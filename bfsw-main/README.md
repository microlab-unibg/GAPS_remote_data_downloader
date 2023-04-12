# Installation

1. install libzmq globally (easy to build from source)
2. install libczmq globally (easy to build from source)
3. mkdir build (from this directory)
4. cd build
5. cmake ..
6. make

The binaries can then be run from the build/bin directory. The source code for the binaries can be found in bfsw/bin.

# Python

The bfsw/pybfsw directory is a python package that contains GSE tools. To use it, do PYTHONPATH=$PYTHONPATH:path/to/bfsw.
external dependencies include:  numpy, pyqt5, pyqtgraph, zmq, rich, rpyc, quickle, textual
