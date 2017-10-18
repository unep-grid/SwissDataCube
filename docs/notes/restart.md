# Restart datacube procedure

```
sudo swapon /swap-1G.img
sudo /etc/init.d/data_cube_ui restart
sudo /etc/init.d/celerybeat restart
source /home/sdcuser/Datacube/datacube_env/bin/activate
export XDG_RUNTIME_DIR=""
jupyter notebook --no-browser --ip='*' --port='8080'
ctrl-z
bg
```
