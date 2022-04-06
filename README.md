# NDP-blueprint

### Installation

##### Prepare system virtual environment (virtualenv)

On ubuntu run as root

```bash
apt install python3-pip libpq-dev
```

##### Create virtual environment (virtualenv)

Log-in as user and run

```bash
cd /path/pattern_solvers

virtualenv pattern_solvers
```


### Activate and update virtual environment (virtualenv)

Login as user and run

```bash
cd /path/pattern_solvers

source pattern_solvers/bin/activate

pip install -r requirements
```


### Run solver

```bash
python3 main.py -v -d inputs/Multi11bit.txt -m lou -t 8
```
