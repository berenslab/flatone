# flatone

A command-line tool to (1) download one EyeWire II neuron mesh as `.obj`, (2) skeletonize it as `.swc` and (3) flatten it automatically.

## Installation and Usage

```bash
# first of all, ensure you have all dependencies ready
## mac
brew update
brew install suite-sparse

## debian
sudo apt-get update
sudo apt-get install build-essential # if not already installed
sudo apt-get install libsuitesparse-dev

# clone this repo 
git clone https://github.com/berenslab/flatone
cd flatone 

# install flatone with uv
uv tool install .

# or install it with pip
pip install -e .
```

Assuming you already have CAVEClient credentials stored in your environment, you can download the mesh, skeletonize it, and flatten it with the current SAC surface mappings with one line in the terminal:

```bash
flatone 7205759405XXXXXXXX
```

This will create a `output` directory in the same directory where you run the line above:

```bash
output
└── 7205759405XXXXXXXX
    ├── mesh_warped.ctm # only if `--warp-mesh` is explicitly set
    ├── mesh.obj
    ├── skeleton_warped.npz
    ├── skeleton_warped.png
    ├── skeleton_warped.swc
    ├── skeleton.npz
    ├── skeleton.png
    ├── skeleton.swc
    └── strat_profile.png
```

You can overwrite a certain step by using `--overwrite-*`. For now there aren't a lot of things to be tuned, except switching between different conformal maps (e.g. `--overwrite-profile --mapping j1`; default we use `j2` which is much faster but slightly less accurate); or using a different z-extends for the stratification profile in `strat_profile.png` (e.g. `--overwrite-profile --z-profile-extends -30 50`).

Run `flatone -h` for more options.