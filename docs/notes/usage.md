# Usage
## Paths

**GEOTIFFS** */datacube/original\_data/&lt;tile&gt;*

**OUTPUTS (NetCDF)** */datacube/ingested\_data/&lt;landsat sat ex: LC8\_OLI\_LEDAPS…&gt;*

**Ingestion Scripts** */home/sdcuser/Datacube/agdc-v2/ingest/ingestion\_configs*

## TMUX

**tmux** - créer une session

**ctrl-b d** - sortir sans arrêter la session

**tmux list-sessions** - lister les sessions tmux:

**tmux attach -t #** - revenir à une session (attach le numero de session)

**exit** - cloturer la session tmux

Plus d&#39;info: https://doc.ubuntu-fr.org/tmux

## INITIALISE (only once)

### a - Clean Data Base (drop schema)**

``` cd /usr/lib/postgresql/9.5/bin*

Be careful next command delete everything in your Cube!! (except data stored in Django db [schema public])

#### psql -d datacube -U postgres -c &#39;DROP SCHEMA agdc CASCADE;&#39;

### b - generate data base (new schema)**

These commands should be run under the Python virtual environment

#### cd ~/Datacube/agdc-v2

#### source ~/Datacube/datacube\_env/bin/activate                        deactivate to exit

#### datacube -v system init

### c – Add product**

Before ingesting any data, a product type must be added to the DataCube. These commands should be run under the Python virtual environment:

Please run one time each of the follows

#### datacube product add ingest/dataset\_types/ls5\_ledaps\_scene.yaml

#### datacube product add ingest/dataset\_types/ls7\_ledaps\_scene.yaml

#### datacube product add ingest/dataset\_types/ls8\_ledaps\_scene.yaml

**ROUTINES**

# **1 – Generate YAML files**

The data then needs to be prepared for ingestion: generation of metadata (YAML format) from MTL metainformation

#### cd /home/sdcuser/Datacube/agdc-v2/datacube/original\_data/LiMES\_run\_&lt;date&gt;/

#### python usgslsprepare\_py35\_mtl.py &lt;tile&gt;/LE7\*   NB run for each tile AND for each LS type (LC(, LE7 LT5)

# **2 – Indexation**

**Indexation** (go to YAML file already generated and transfer the info into Postgres database)

#### cd ~/Datacube/agdc-v2

#### datacube dataset add /datacube/original\_data/\*/\* --auto-match

This task is fast (less than a second per image)

#### _datacube dataset add /datacube/original\_data/LC8/\*/\* --dtype_ ls8\_ledaps\_scene\_lm  (example for adding others datasets in same cube)

# **3 – Ingestion**

#### datacube -v ingest -c /home/sdcuser/Datacube/agdc-v2/ingest/ingestion\_configs/ls7\_ledaps\_ch\_ll.yaml        NB run 3 times one per each ingestion file

**Ingestion files are:**

### Ls5\_ledaps\_ch\_ll.yaml

### ls7\_ledaps\_ch\_ll.yaml

### ls8\_ledaps\_ch\_ll.yaml

**INFO**

#### cd ~/Datacube/agdc-v2

#### source ~/Datacube/datacube\_env/bin/activate

#### datacube product list

#### python examples/andrea\_tests/info\_prod.py

#### TO see netCDF datasets (All tiles)

#### psql -d datacube -U postgres -c &#39;SELECT time, lat, lon, platform  FROM agdc.dv\_ls8\_ledaps\_swiss\_dataset&#39;;                -- repeat with ls5 and ls7

q                --exit psql console

#### TO see **SCENE-ID** datasets (only original Geotiff scenes)

#### psql -d datacube -U postgres -c &#39;SELECT a.uri\_body, a.added FROM agdc.dataset\_location AS a INNER JOIN agdc.dataset  AS b ON a.dataset\_ref = b.&quot;id&quot; WHERE b.dataset\_type\_ref &lt; 4&#39;;

q                --exit psql console

#### TO see **SCENE-ID** datasets (All geotiff + NetCdf)

#### psql -d datacube -U postgres -c &#39;SELECT uri\_body, added  FROM agdc.dataset\_location&#39;;

q                --exit psql console

**OPERATIONS ON DATABASE (modifications !!!)**

#### TO clean last records

#### psql -d datacube -U postgres

#### SELECT stat.clean\_last\_records(&#39;2017:05:29&#39;);

\q                --exit psql console

