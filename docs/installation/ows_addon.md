# OWS addon installation
## Installation
```
su localuser
cd ~/Datacube
conda deactivate  (needed only for dev and test for which test was done with conda)
virtualenv -p /usr/bin/python3 odc_env
source odc_env/bin/activate
git clone https://github.com/opendatacube/datacube-ows.git
cd datacube-ows
pip install --pre -r requirements.txt
cd datacube_ows
```
## Configuration
ows_cfg.py (Bruno’s file)
```
"allowed_urls": ["http://sdc.unepgrid.ch/ows","http://sdc.unepgrid.ch:5000"],
```
## Database update
```
cd ~/Datacube/datacube-ows
pip install PyCRS
pip install PyPI
export DB_USERNAME=dc_user
export DB_PASSWORD=****
export DB_HOSTNAME=localhost
export DB_DATABASE=datacube

python update_ranges.py –schema --role dc_user 

python update_ranges.py --multiproduct ls8_lasrc_swiss --no-calculate-extent
```

## Webserver: Test with flask
export FLASK_APP=datacube_ows/ogc.py
flask run --host=129.194.205.59

http://sdc.unepgrid.ch:5000/

## Gunicorn installation
```
pip install gunicorn
```
vi ~/Datacube/datacube-ows/wsgi.py
```
#pylint: skip-file
import sys
import os

# This is the directory of the source code that the web app will run from
sys.path.append("/home/localuser/Datacube/")

# The location of the datcube config file.
os.environ.setdefault("DATACUBE_CONFIG_PATH", "/home/localuser/.datacube.conf")

from datacube_ows.ogc import app
application = app

def main():
    app.run()


if __name__ == '__main__':
    main()
```
gunicorn --bind 0.0.0.0:5000 wsgi &

## Apache proxying
```
a2enmod rewrite
a2enmod proxy_http
a2enmod proxy_balancer
```
modify /etc/apache2/sites-enabled/dc_ui.conf
add:
```
        <Proxy *>
                Order deny,allow
                Allow from all
        </Proxy>

        ProxyPass /ows http://sdc.unepgrid.ch:5000
        ProxyPassReverse /ows http://sdc.unepgrid.ch:5000
```
Test: http://sdc.unepgrid.ch/ows/?time=2018-06-10&crs=EPSG:4326&transparent=true&format=image/png&exceptions=application/vnd.ogc.se_xml&styles=&tiled=true&service=WMS&version=1.3.0&request=GetMap&layers=ls8_lasrc_swiss&bbox=46.1,6.0,46.3,6.2&width=256&height=256&layers=ls8_lasrc_swiss


## Start/stop procedure
Check if it works: ps -ef | grep gunicorn
Check main page: http://sdc.unepgrid.ch/ows
 
 
(the acces page is customizable: /home/localuser/Datacube/datacube-ows/datacube_ows/templates/index.html)

stop gunicorn: 
```
pkill -f gunicorn
```
start gunicorn:
```
su localuser
cd ~/Datacube
source odc_env/bin/activate
cd datacube-ows
gunicorn --bind 0.0.0.0:5000 wsgi &
```
