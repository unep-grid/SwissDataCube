# Restart datacube procedure

```
sudo /etc/init.d/data_cube_ui restart
sudo /etc/init.d/celerybeat restart
export XDG_RUNTIME_DIR=""
jupyter notebook --no-browser --ip='*' --port='8080'
ctrl-z
bg
```
