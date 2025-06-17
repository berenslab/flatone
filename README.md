# flatone

A command-line tool to (1) download one EyeWire II neuron mesh as `.obj`, (2) skeletonize it as `.swc` and (3) flatten it automatically.

## Installation and Usage

```bash
# prerequisites
## mac
brew update
brew install suite-sparse

## debian/ubuntu/WSL
sudo apt-get update
sudo apt-get install build-essential # if not already installed
sudo apt-get install libsuitesparse-dev

# clone this repo 
git clone https://github.com/berenslab/flatone
cd flatone 

# install with uv
uv tool install .

# or with pip
pip install -e .
```

Assuming you have a CAVEClient token stored in your environment, you can run the full pipeline in one line:

```bash
flatone SEGMENT_ID
```

(If you don't have a CAVEClient token yet, `flatone` will call `CAVEclient().auth.get_new_token()`, which will guide you to a website to get a new token. After that, you can run `flatone add-token YOUR-NEW-TOKEN` to save it to the environment and then run `flatone SEGMENT_ID` again.)

This creates an `output` directory in the working directory:

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

`flatone` currently supports a handful (but very limited) of customization:

- `--overwrite-*` flags redo individual steps;
- switch the conformal map with `--mapping j1` (default `j2`: much faster, but slightly less accurate);
- change the z-extends for the stratification profile, e.g.: `flatone SEG_ID --overwrite-profile --z-profile-extends -30 50`

Run `flatone -h` for more options.