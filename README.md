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
git clone git@github.com:berenslab/flatone.git
cd flatone 

# install with uv to the global environment
uv tool install .

# or with pip (also to the global environment)
pip install -e .

# but it's highly recommended to install it within a venv env
# here we use uv again but of course you can run python -m venv 
uv venv .venv --python 3.13
source .venv/bin/activate
uv pip install -e .

# now you can check if it works
flatone -v 
```

Assuming you have a CAVEClient token stored in your environment, you can run the full pipeline in one line:

```bash
flatone SEGMENT_ID
```

(If you don't have a CAVEClient token yet, `flatone` will call `CAVEclient().auth.get_new_token()` automatically, which will guide you to a website to get a new token (you don't need to follow all the steps from the CAVEClient, you only need to go to the link, and get the token). After that, you can run `flatone add-token YOUR-NEW-TOKEN` to save it to the environment and then run `flatone SEGMENT_ID` again.)

This creates an `output` directory in the working directory:

```bash
output
└── 7205759405XXXXXXXX
    ├── mesh_warped.obj # only if `--warp-mesh` is explicitly set
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
- change the z-extends for the stratification profile, e.g.: `flatone SEG_ID --overwrite-profile --z-profile-extent -30 50`

You can also warp the mesh, but it's not in the default as it's a much slower process and not always needed to do. You can run `flatone SEGMENT_ID --warp-mesh` to warp the mesh (and the previous steps will not be recomputed unless you also provide any of the `--overwrite*` flags).

`flatone` also has a (limited) interactive 3d viewer, which you can activate via `flatone view3d`. You can append a SEGMENT_ID after it to just view this cell, or without it, to view all cells within the `output/` folder. By default, it will view the unwarped meshes and skeletons together, if you warped the mesh already, you can also view the warped meshes and skeletons with `flatone view3d --warped`. You can also curate a different set of cells in another folder, then view them with `flatone view3d --warped --output-dir="path/to/another/folder".

Check `flatone -h` for more details.

