#!/usr/bin/env python3
import argparse
import re
import sys
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import skeliner as sk
from cloudvolume import CloudVolume
from pywarper import Warper
from pywarper.warpers import warp_mesh as warp_mesh_fn

try:
    __version__ = version("flatone")
except PackageNotFoundError:
    __version__ = "unknown"

_MAPPING_RE: Final = re.compile(r"^global_map_(?P<flavour>j\d)_(?P<date>\d{8})\.npz$")

def _resolve_mapping_file(selector: str | Path) -> Path:
    """
    Turn *selector* into a concrete ``Path`` to a mapping file.

    Parameters
    ----------
    selector
        • 'j1' or 'j2'  →  pick the latest matching file shipped in
          ``flatone/cached/`` (by date suffix).
        • any other string or Path → treated as an explicit path;
          it must exist.

    Returns
    -------
    pathlib.Path
        Path to the .npz file.

    Raises
    ------
    FileNotFoundError
        If no suitable file is found.
    ValueError
        If *selector* looks like j-flavour but no corresponding file exists.
    """
    sel = str(selector)

    # explicit path ----------------------------------------------------------
    p = Path(sel)
    if p.suffix == ".npz" and p.exists():
        return p.expanduser().resolve()

    # j-flavour --------------------------------------------------------------
    if sel in {"j1", "j2"}:
        cached = resources.files("flatone").joinpath("cached")
        # collect all matching files, keep the newest by date
        candidates: list[tuple[str, Path]] = []
        for file in cached.iterdir():
            m = _MAPPING_RE.match(file.name)
            if m and m.group("flavour") == sel:
                candidates.append((m.group("date"), file))
        if not candidates:
            raise FileNotFoundError(
                f"No global mapping with flavour '{sel}' found in flatone/cached"
            )
        newest = max(candidates, key=lambda t: t[0])[1]
        return newest

    # fallthrough ------------------------------------------------------------
    raise ValueError(
        f"Unrecognised mapping selector '{selector}'. "
        "Use 'j1', 'j2', or a path to a .npz file."
    )


def _load_global_mapping(selector: str | Path = "j2") -> dict:
    """Load the global mapping of segment-IDs to names."""
    path = _resolve_mapping_file(selector)
    with np.load(path, allow_pickle=True) as z:
        return {k: v for k, v in z.items()}

def _build_token_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flatone add-token",
        description="Save a CAVEclient token for future sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("token", help="token string obtained from the DAF portal")
    return p

# ---------- pure functions ------------------------------------------------- #

def fetch_mesh(seg_id: int, outdir: Path, verbose: bool, overwrite: bool) -> Path:
    """Download → dedupe → save OBJ mesh; return path."""

    # check caveclient credentials before proceeding
    from caveclient import CAVEclient
    client = CAVEclient()

    if client.auth.token is None:
        print("No CAVEclient token found.\n")
        _ = client.auth.get_new_token()
        raise SystemExit("\nRun `flatone add-token xxxxx` to add a token.")

    mesh_path = outdir / "mesh.obj"
    if not overwrite and mesh_path.exists():
        if verbose:
            print(f"Mesh for segment {seg_id} already exists at: ")
            print(f"  {mesh_path}\n")
        return mesh_path

    if verbose:
        print(f"Fetching mesh for segment {seg_id} …")
    cv = CloudVolume(
        "graphene://middleauth+https://minnie.microns-daf.com/segmentation/table/stroeh_mouse_retina/",
        use_https=True,
        progress=True,
    )
    mesh = cv.mesh.get(seg_id, remove_duplicate_vertices=True)[seg_id]
    mesh_path.write_bytes(mesh.to_obj())
    if verbose:
        print("Saved mesh to:")
        print(f"  {mesh_path}\n")
    return mesh_path



def build_skeleton(mesh_path: Path, outdir: Path,
                   seg_id: int, verbose: bool, overwrite: bool) -> Path:
    """Skeletonise mesh, save SWC & preview PNG; return SWC path."""
    skel_path = outdir / "skeleton.swc"
    npz_path = outdir / "skeleton.npz"
    preview   = outdir / "skeleton.png"

    if not overwrite and skel_path.exists() and preview.exists():
        if verbose:
            print(f"Skeleton for segment {seg_id} already exists at:")
            print(f"  {skel_path}\n")
        return skel_path

    if verbose:
        print("Skeletonising …")
    mesh = sk.io.load_mesh(mesh_path)                 # nm
    skel = sk.skeletonize(mesh, verbose=verbose, id=seg_id)      # nm

    fig, ax = sk.plot3v(
        skel, mesh, scale=1e-3, unit='μm',
        title=f"{seg_id}", color_by="ntype", skel_cmap="Set2",
    )
    fig.savefig(preview, dpi=300, bbox_inches="tight")
    plt.close(fig)

    skel.convert_unit(target_unit="μm")
    skel.to_swc(skel_path)               
    skel.to_npz(npz_path)
    if verbose:
        print("Saved skeleton and plot to: ")
        print(f"  {skel_path}")
        print(f"  {npz_path}")
        print(f"  {preview}")
        print("\n")
    return skel_path


def warp_skeleton(
    skel_path: Path,
    outdir: Path,
    seg_id: int,
    mapping: dict,
    z_profile_extent: list[float] | None = None,
    verbose: bool = False,
    overwrite: bool = False,
) -> None:
    """Warp arbor to SAC sheets; save warped view & depth profile."""
    warped_swc = outdir / "skeleton_warped.swc"
    wapred_npz = outdir / "skeleton_warped.npz"
    warped_png = outdir / "skeleton_warped.png"
    profile_png = outdir / "strat_profile.png"

    if not overwrite and warped_png.exists() and profile_png.exists():
        if verbose:
            print("Warped arbor and depth profile already exist at:")
            print(f"  {warped_swc}")
            print(f"  {wapred_npz}")
            print(f"  {warped_png}")
            print(f"  {profile_png}")
            print("\n")
        return

    if verbose:
        print("Warping arbor and building Z-profile …")

    w = Warper(verbose=verbose)

    # w.on_sac_surface, w.off_sac_surface = _load_sac_surfaces()

    w.skeleton = sk.io.load_swc(skel_path)            # μm
    w.mapping = mapping
    w.warp_skeleton(z_profile_extent=z_profile_extent)

    w.warped_skeleton.to_swc(warped_swc)  # μm
    w.warped_skeleton.to_npz(outdir / "skeleton_warped.npz")
    # 3-D warped view -------------------------------------------------------
    fig, ax = sk.plot3v(
        w.warped_skeleton, scale=1, unit='μm',
        color_by="ntype", skel_cmap="Set2", title=f"{seg_id} (warped)",
    )

    fig.savefig(warped_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Flattened view + Z-profile -------------------------------------------
    ###############################################################################
    # --- constants ---------------------------------------------------------------
    FIG_H_IN      = 4.0       # fixed physical height  [inch]
    RIGHT_W_IN    = 1.25      # physical width of the right pane [inch]
    BASE_FS_PT = 0.030 * FIG_H_IN * 72            # 3 % of fig-height
    mpl.rcParams.update({                         # applied once per script
        "font.size"        : BASE_FS_PT,
        "axes.labelsize"   : BASE_FS_PT * 0.8,
        "axes.titlesize"   : BASE_FS_PT * 1,
        "xtick.labelsize"  : BASE_FS_PT * 0.75,
        "ytick.labelsize"  : BASE_FS_PT * 0.75,
        "legend.fontsize"  : BASE_FS_PT * 0.75,
    })
        
    ###############################################################################

    # --------------------------------------------------------------------------- #
    # 1.  Work out how wide the *left* pane must be so that 1 µm on X == 1 µm on Z
    # --------------------------------------------------------------------------- #
    xyz         = w.warped_skeleton.nodes                # (N, 3) columns → (x, y, z)
    x_span_um   = np.ptp(xyz[:, 0])
    z_span_um   = np.ptp(xyz[:, 2])
    LEFT_W_IN   = FIG_H_IN * (x_span_um / z_span_um)  # 1:1 scale
    FIG_W_IN    = LEFT_W_IN + RIGHT_W_IN              # total figure width

    # --------------------------------------------------------------------------- #
    # 2.  Make the figure — NO gap between the two cells
    # --------------------------------------------------------------------------- #
    fig, (ax_nodes, ax_prof) = plt.subplots(
        1, 2,
        figsize=(FIG_W_IN, FIG_H_IN),
        sharey=True,
        gridspec_kw={'width_ratios': [LEFT_W_IN, RIGHT_W_IN], 'wspace': 0}
    )

    # critical: push the *patch* of each axes against the neighbour
    ax_nodes.set_anchor('E')   # left pane anchored to its *east* side
    ax_prof.set_anchor('W')    # right pane anchored to its *west* side

    # --------------------------------------------------------------------------- #
    # 3.  Left panel — arbor, true 1:1 scale
    # --------------------------------------------------------------------------- #
    sk.plot2d(w.warped_skeleton, plane="xz",
            ax=ax_nodes, color_by="ntype", skel_cmap="Set2")
    ax_nodes.set_xlabel('X (µm)')
    ax_nodes.set_ylabel('Z (µm)')
    ax_nodes.set_aspect('equal', adjustable='box')     # keep the scale

    colors = ["C3", "C0"]
    for i, y in enumerate((0, 12)):
        ax_nodes.axhline(y, ls='--', c=colors[i])
    ax_nodes.text(ax_nodes.get_xlim()[1],  0, 'ON SAC ',  va='bottom', ha='right', fontsize=10, color=colors[0])
    ax_nodes.text(ax_nodes.get_xlim()[1], 12, 'OFF SAC ', va='bottom', ha='right', fontsize=10, color=colors[1])
    ax_nodes.spines['top'].set_visible(False)
    ax_nodes.spines['right'].set_visible(False)
    ax_nodes.set_title(f"{seg_id}")
    # --------------------------------------------------------------------------- #
    # 4.  Right panel — fixed-width stratification profile
    # --------------------------------------------------------------------------- #
    zp = w.warped_skeleton.extra["z_profile"]
    ax_prof.plot(zp["distribution"], zp["x"], lw=2, c='black')
    ax_prof.barh(zp["x"], zp["histogram"], color='gray', alpha=0.5)
    ax_prof.set_xlabel('dendritic length')
    ax_prof.set_title('Z-Profile')

    ax_prof.axhline(0,  ls='--', c=colors[0])
    ax_prof.axhline(12, ls='--', c=colors[1])
    ax_prof.spines['top'  ].set_visible(False)
    ax_prof.spines['right'].set_visible(False)

    for ax in (ax_nodes, ax_prof):
        ax.set_ylim(z_profile_extent)


    # --------------------------------------------------------------------------- #
    fig.tight_layout(pad=0, rect=(0., 0., 1., 0.93))


    fig.savefig(profile_png, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    if verbose:
        print("Skeleton warp/profile complete.")
        print("Saved warped skeleton and stratification profile to:")
        print(f"  {outdir / 'skeleton_warped.swc'}")
        print(f"  {outdir / 'skeleton_warped.npz'}")
        print(f"  {warped_png}")
        print(f"  {profile_png}")
        print("\n")



def warp_mesh_and_save(
    mesh_path: Path,
    outdir: Path,
    mapping: dict,
    verbose: bool,
    overwrite: bool,
) -> None:
    """Warp the *raw mesh* and save as OBJ."""
    warped_path = outdir / "mesh_warped.obj"
    if warped_path.exists() and not overwrite:
        if verbose:
            print("Warped mesh already exists at:")
            print(f"  {warped_path}\n")
        return

    if verbose:
        print("Warping raw mesh (may be slow) …")
    mesh = sk.io.load_mesh(mesh_path)  # nm
    warped_mesh = warp_mesh_fn(mesh, mapping, mesh_vertices_scale=1e-3, verbose=verbose)
    sk.io.to_ctm(warped_mesh, warped_path)
    warped_mesh.export(warped_path)
    if verbose:
        print("Saved warped mesh to:")
        print(f"  {warped_path}\n")

def _gather_all_segids(root_out: Path) -> list[int]:
    """Return sorted list of numeric sub-dir names in *root_out*."""
    return sorted(
        int(p.name) for p in root_out.iterdir() if p.is_dir() and p.name.isdigit()
    )

def run_3dviewer(seg_ids: list[int], root_out: Path, warped: bool) -> None:
    """
    Load mesh/skeleton pairs for *all* seg_ids and launch microviewer.

    Aborts if any required file is missing.
    """

    if not seg_ids:
        seg_ids = _gather_all_segids(root_out)
        if not seg_ids:
            raise SystemExit(f"No segment folders found in {root_out}")

    meshes: list = []
    skels: list = []
    missing: list = []

    for sid in seg_ids:
        seg_dir = root_out / str(sid)
        mesh_path = seg_dir / ("mesh_warped.obj" if warped else "mesh.obj")
        skel_path = seg_dir / ("skeleton_warped.swc" if warped else "skeleton.swc")

        if not (mesh_path.exists() and skel_path.exists()):
            missing.append((sid, mesh_path, skel_path))
            continue

        meshes.append(sk.io.load_mesh(mesh_path))
        skels.append(sk.io.load_swc(skel_path))

    if missing:
        msg = ["Missing files:"]
        for sid, m, s in missing:
            msg.append(f"  {sid}: {m if not m.exists() else ''} {s if not s.exists() else ''}")
        msg.append("\nRun the 'process' pipeline first "
                   "(add --warp-mesh if you want warped data).")
        raise SystemExit("\n".join(msg))

    # skeliner.plot.view3d can now take lists:
    # pass a *pair* of scales → (skeleton_scale, mesh_scale)
    sk.plot.view3d(skels, meshes, scale=(1, 1e-3))


# ---------- CLI entry-point ---------------------------------------------- #


# ──────────────────────────────────────────────────────────────────────
# CLI helpers
# ──────────────────────────────────────────────────────────────────────
def _build_pipeline_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flatone",
        description="Flatten one Eyewire-II neuron automatically.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # mandatory segment ID
    p.add_argument("seg_id", type=int, help="EM segment ID")

    # I/O
    p.add_argument("--output-dir", type=Path, default=Path("./output"),
                   help="directory for meshes, skeletons, and plots")

    # overwrite flags
    g = p.add_argument_group("overwrite")
    g.add_argument("--overwrite", action="store_true")
    g.add_argument("--overwrite-mesh", action="store_true")
    g.add_argument("--overwrite-skeleton", action="store_true")
    g.add_argument("--overwrite-profile", action="store_true")
    g.add_argument("--overwrite-warped-mesh", action="store_true")

    # other options
    p.add_argument("--no-verbose", dest="verbose", action="store_false")
    p.add_argument("--z-profile-extent", type=float, nargs=2,
                   default=[-25.0, 40.0], metavar=("Z_MIN", "Z_MAX"))
    p.add_argument("-m", "--mapping", default="j2",
                   help="mapping: 'j1', 'j2' (default) or path to .npz")
    p.add_argument("--warp-mesh", action="store_true",
                   help="also warp the raw mesh")

    p.add_argument('-v', '--version', action='version', version=__version__, help="show version")

    return p


def _build_viewer_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flatone view3d",
        description="Interactive 3-D viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p.add_argument("seg_ids", type=int, nargs="*", metavar="SEG_ID",
                   help="zero or more segment IDs (omit to load every folder "
                        "under --output-dir)")
    p.add_argument("--output-dir", type=Path, default=Path("./output"),
                   help="root directory containing segment sub-folders")
    p.add_argument("--warped", action="store_true",
                   help="show warped mesh + warped skeleton")
    return p


def _print_top_help() -> None:
    """Combined help when user calls just `flatone -h`."""
    _build_pipeline_parser().print_help()
    print(
        "\nSUB-COMMANDS\n"
        "  view3d      interactive 3-D viewer\n"
        "  add-token   store a CAVEclient token\n"
        "\nRun  “flatone <sub-command> -h”  for details.\n"
    )
    sys.exit(0)


# ──────────────────────────────────────────────────────────────────────
# Main entry-point
# ──────────────────────────────────────────────────────────────────────
def main() -> None:
    argv = sys.argv[1:]

    # handle --version / -v
    if "-v" in argv or "--version" in argv:
        print(__version__)
        return

    # top-level help
    if not argv or argv[0] in ("-h", "--help"):
        _print_top_help()

    # add caveclient token
    if argv[0] == "add-token":
        args = _build_token_parser().parse_args(argv[1:])
        from caveclient import CAVEclient
        CAVEclient().auth.save_token(token=args.token)
        print("Token saved. You can now try running `flatone SEG_ID` again.")
        return

    # skeliner.view3d
    if argv[0] == "view3d":
        args = _build_viewer_parser().parse_args(argv[1:])
        run_3dviewer(args.seg_ids, args.output_dir, warped=args.warped)
        return

    # otherwise: pipeline
    args = _build_pipeline_parser().parse_args(argv)

    outdir = args.output_dir / str(args.seg_id)
    outdir.mkdir(parents=True, exist_ok=True)

    ow_mesh = args.overwrite or args.overwrite_mesh
    ow_skel = args.overwrite or args.overwrite_skeleton
    ow_prof = args.overwrite or args.overwrite_profile
    ow_meshwarp = args.overwrite or args.overwrite_warped_mesh

    mesh_path = fetch_mesh(args.seg_id, outdir, args.verbose, ow_mesh)
    skel_path = build_skeleton(mesh_path, outdir, args.seg_id,
                               args.verbose, ow_skel)
    mapping = _load_global_mapping(args.mapping)

    warp_skeleton(skel_path, outdir, args.seg_id, mapping,
                  z_profile_extent=args.z_profile_extent,
                  verbose=args.verbose, overwrite=ow_prof)

    if args.warp_mesh:
        warp_mesh_and_save(mesh_path, outdir, mapping,
                           args.verbose, ow_meshwarp)


if __name__ == "__main__":
    main()