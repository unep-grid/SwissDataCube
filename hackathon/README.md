# SDC Hackathon 11-13 April 2018
Info & registration: http://www.swissdatacube.org/index.php/2018/03/07/opengeneva-hackathon-sdc-sdg/

## News 1 [April 3]
1. We will start on Wednesday April 11 at 9:00. The event will finish on Friday April 13 at 17:00.
2. The venue will be at the "Centre Universitaire d’Informatique”, 7 route de Drize, 1227 Carouge. You can find access information on the following page: http://cui.unige.ch/en/contact/planaccessglobal/
3. We will have a dedicated GitHub repository available at: https://github.com/GRIDgva/SwissDataCube/tree/master/hackathon
4. Currently, we are working with our NASA colleagues to prepare a Virtual Machine with all the necessary material to work with. As soon as it will be ready, we will send you the link to download and install it.

## News 2 [April 4]
The rooms for our Hackathon will be the following 301-2 [April 11]; 322-3 [April 12-13]

## Swiss Data Cube Virtual Machine
1. You need first to install Virtual Box: https://www.virtualbox.org
2. Then download the SDC VM at: https://owncloud.unepgrid.ch/index.php/s/tsmakvA29MIx1UZ
3. Import the downloaded OVA file in Virtual Box (Import Appliance)
4. Download and mount the virtual data disk [available soon]
5. In order to bypass firewall issue in Linux and Mac OS change the guest SSH port to 3022
```
Settings > Network > Advanced > Port Forwarding > Change SSH Host Port from 222 to 3022 > OK > OK
```

The VM is a minimial installation with no data (just the OS, the UI, and the notebook server).

Data are available on a separate virtual data disk which can be mounted to the VM.

The VM is configured with 2 vCPUs and 2 GB RAM.
```
username: localuser/password: localuser1234
```
Start the VM in Headless mode

Connect to the VM using SSH (terminal or Putty) in order to allow copy/paste
```
ssh -p 3022 localuser@localhost
```

To start the User Interface (http://localhost:8000/), type the following command line:
```
sudo service data_cube_ui restart 
```
To start the Jupyter Notebook (http://localhost:8888), type the following command line:
```
source ~/Datacube/datacube_env/bin/activate
cd ~/Datacube/data_cube_notebooks/
jupyter notebook
Ctrl+Z
bg
deactivate
```
