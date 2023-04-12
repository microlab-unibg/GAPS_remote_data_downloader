# TODO 

## High priority
* gsedb refactor into app class, improve ctor and dtor for db writers and finally fix the issue with closing the db on exit, add second argument
* remove asserts, replace with return code
* in templated functions that take bytes as input, implement some sort of enforcement that element of the container is an unsigned char. concepts? type traits? static\_assert?
* in unpack methods, add some more checks, like on packet type
* event builder: check flag for tof triggered mode
* define ACK packet
* audit zmq water mark issue
* add more metadata to mergedevent table, fill out ntofhits field
* cmake install targets
* debug issue where files on gfp computer were opened and closed 2 seconds later with 0 data (note this wasn't happening on gaps-gfp, just gfp) 

## Medium priority
* in gsedb, generate a packet with statistics (like data rate, number of good packets, number of parse errors) etc., and insert that into the DB every 10 seconds or so.  This will allow us to use the stripchart to plot the data rate and other nice features.
* stripchart: some way of indicating when datapoints overlap.  the problem is if you get many datapoints from the same 64 ms time bin, and the y value is the same, then you wouldn't know from looking at the GSE.  One possibility is to add some random x-axis noise to points that overlap, the magnitude of this noise should be small, like a few ms, smaller than 64 ms granularity timestamp
* in stripchart, option to force separate plot panes even when units are the same
* implement scheme for retrieving raw data from a name that has a converter specified (not just the converted values)
	* this could just be a convert=True keyword in the query methods
* add floating point rounding logic to timestamp calculations.

## Low Priority
* add a downsample parameter for each trace (e.g. 4 -> plot every 4th data point)
* cycle stripchart colors
* logger: don't add .bin extension until file is done.  this way, all closed files can be gzipped in place without danger of gzipping the currently open file.
	* one posible issue with this is that if the process is killed you will be left with a file without an extension.  this might be OK, but 
