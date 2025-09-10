# flatone

A command-line tool that automatically (1) downloads the mesh of an EyeWire II neuron as `.obj` with [CaveClient/CloudVolume](https://github.com/seung-lab/cloud-volume), (2) skeletonizes it as an `.swc` with [skeliner](https://github.com/berenslab/skeliner) and (3) flattens it with [pywarper](https://github.com/berenslab/pywarper).

> __NOTE__ 
> 
> `flatone` is designed for quick, exploratory inspection. Skeletons and warps are generated with the default parameters of `skeliner` and `pywarper`, most of them cannot be tuned directly in `flatone`, so results might not be optimal for some cells. For higher-precision results, run `skeliner` and `pywarper` directly and fine-tune the parameters.


## Installation

`flatone` relies on SuiteSparse, which does **NOT** run on native Windows. Use it on Unix-like enviroment or Windows Subsystem for Linux (WSL 2) instead.


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
uv venv .venv --python 3.13 # any versions>=3.10 should work
source .venv/bin/activate
uv pip install -e .

# now you can check if it works
flatone -v 
```

## Usage

All you need to do is provide the segment ID of an EW2 neuron you'd like to preview: 

```bash
flatone SEGMENT_ID
```

If you don't have a CAVEClient token stored in the system yet, `flatone` will call `CAVEclient().auth.get_new_token()` internally,  and prints something like:

```
No CAVEclient token found.

New Tokens need to be acquired by hand. Please follow the following steps:
    1) Go to: https://<URL>
    2) Log in with your Google account and copy the token shown.
    3) Add it to Flatone with:
    flatone add-token <TOKEN>
    Note: ...
    Warning! ...
```

Just follow the link, copy the token, and register it with:

```bash
flatone add-token <TOKEN>
```

The token is stored in `~/.cloudvolume/secrets`. Now you can rerun the command:

```bash
flatone SEGMENT_ID
```

This will create an `output` directory in the same directory:

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
- change the soma detection threshold if the default failed, e.g.: `flatone SEG_ID --soma-threshold 90 --overwrite-skeleton --overwrite-profile`
- change the initial soma guess (needed if there's no soma in the mesh), e.g.: `flatone SEG_ID --soma-init-guess-mode max --overwrite-skeleton --overwrite-profile`

You can also warp the mesh, but it's not in the default as it's a much slower process and not always needed to do. You can run `flatone SEGMENT_ID --warp-mesh` to warp the mesh (and the previous steps will not be recomputed unless you also provide any of the `--overwrite*` flags).

`flatone` also has a (limited) interactive 3d viewer, which you can activate via `flatone view3d`. You can append a SEGMENT_ID after it to just view this cell, or without it, to view all cells within the `output/` folder. By default, it will view the unwarped meshes and skeletons together, if you warped the mesh already, you can also view the warped meshes and skeletons with `flatone view3d --warped`. You can also curate a different set of cells in another folder, then view them with `flatone view3d --warped --output-dir="path/to/another/folder".

Check `flatone -h` for more details.
