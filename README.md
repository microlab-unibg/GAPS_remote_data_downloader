# GAPS Remote Data Downloader
This repository contains all the code related to the Python function that allows to remotely download data from the GSE database.

### SSH connection to remote GSE machine
`ssh -L 44555:localhost:44555 nadir@128.32.13.79 -p 55225`

![image](https://user-images.githubusercontent.com/36998696/231707102-47356f70-a4fc-48d0-b405-9badaa8f1623.png)

### Data download
`python donwload_data_GAPS_db.py`

![image](https://user-images.githubusercontent.com/36998696/231707949-f73beff6-ae3b-4496-8c43-9849b49fb0ca.png)


### Data format
![image](https://user-images.githubusercontent.com/36998696/231710480-054d76c4-8dd7-4002-aacb-e371690307d9.png)
