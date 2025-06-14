# flatone

A commandline tool to (1) download one EyeWire II neuron mesh as `.obj`, (2) skeletonize it as `.swc` and (3) flatten it automatically.

## Installation and Usage

```bash
# install system dependencies
## mac
brew install suite-sparse

## debian
sudo apt-get install libsuitesparse-dev

# install flatone
uv tool install .
```

Assuming you already have CAVEClient credentials stored in your environment, you can download the mesh, skeletonize it, and flatten it with the current SAC surface mappings with one line in the terminal:

```
flatone 7205759405XXXXXXXX
```

Run `flatone -h` for more options.

