#!/usr/bin/env python3
"""
retina_cli.py – CLI wrapper for skeletonising and warping mouse-retina arbors.

Example:
    ./retina_cli.py 720575940557358735 \
        --output-dir ../output \
        --no-verbose            # silence progress printing
"""

import argparse
import os
from importlib import resources
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import skeliner as sk
from cloudvolume import CloudVolume
from pywarper import Warper


def _load_sac_surfaces() -> tuple[np.ndarray, np.ndarray]:
    path = resources.files("flatone").joinpath("cached", "sac_surfaces.npz")
    with resources.as_file(path) as npz_path, np.load(npz_path, allow_pickle=True) as z:
        return z["on_sac_surface"], z["off_sac_surface"]


# ---------- pure functions ------------------------------------------------- #

def fetch_mesh(seg_id: int, outdir: Path, verbose: bool, overwrite: bool) -> Path:
    """Download → dedupe → save OBJ mesh; return path."""
    mesh_path = outdir / "mesh.obj"
    if not overwrite and mesh_path.exists():
        if verbose:
            print(f"Mesh for segment {seg_id} already exists.")
        return mesh_path

    if verbose:
        print(f"Fetching mesh for segment {seg_id} …")
    cv = CloudVolume(
        "graphene://middleauth+https://minnie.microns-daf.com/segmentation/table/stroeh_mouse_retina/",
        use_https=True,
        progress=verbose,
    )
    mesh = cv.mesh.get(seg_id, remove_duplicate_vertices=True)[seg_id]
    mesh_path.write_bytes(mesh.to_obj())
    if verbose:
        print(f"Saved mesh to {mesh_path}")
    return mesh_path



def build_skeleton(mesh_path: Path, outdir: Path,
                   seg_id: int, verbose: bool, overwrite: bool) -> Path:
    """Skeletonise mesh, save SWC & preview PNG; return SWC path."""
    skel_path = outdir / "skeleton.swc"
    preview   = outdir / "skeleton.png"

    if not overwrite and skel_path.exists() and preview.exists():
        if verbose:
            print(f"Skeleton for segment {seg_id} already exists.")
        return skel_path

    if verbose:
        print("Skeletonising …")
    mesh = sk.io.load_mesh(mesh_path)                 # nm
    skel = sk.skeletonize(mesh, verbose=verbose)      # nm

    fig, ax = sk.plot3v(
        skel, mesh, scale=1e-3, unit='μm',
        title=f"{seg_id}", color_by="ntype", skel_cmap="Set2",
    )
    fig.savefig(preview, dpi=300, bbox_inches="tight")
    plt.close(fig)

    skel.to_swc(skel_path, scale=1e-3)                # μm
    if verbose:
        print(f"Saved skeleton and plot to {outdir}")
    return skel_path

def warp_and_profile(skel_path: Path, outdir: Path,
                     verbose: bool, overwrite: bool) -> None:
    """Warp arbor to SAC sheets; save warped view & depth profile."""
    warped_png = outdir / "skeleton_warped.png"
    profile_png = outdir / "strat_profile.png"

    if not overwrite and warped_png.exists() and profile_png.exists():
        if verbose:
            print("Warped arbor and depth profile already exist.")
        return

    if verbose:
        print("Warping arbor and building Z-profile …")

    w = Warper(verbose=verbose)

    # with np.load("./cached/sac_surfaces.npz", allow_pickle=True) as z:
    #     w.on_sac_surface  = z['on_sac_surface']   # μm
    #     w.off_sac_surface = z['off_sac_surface']  # μm
    w.on_sac_surface, w.off_sac_surface = _load_sac_surfaces()

    w.skel = sk.io.load_swc(skel_path)            # μm

    w.build_mapping()
    w.warp_arbor()
    w.get_arbor_density()

    # 3-D warped view -------------------------------------------------------
    fig, ax = sk.plot3v(
        w.normed_arbor, scale=1, unit='μm',
        color_by="ntype", skel_cmap="Set2",
    )
    fig.savefig(warped_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Flattened view + Z-profile -------------------------------------------
    fig, (ax_nodes, ax_prof) = plt.subplots(
        1, 2, figsize=(8, 4), sharey=True,
        gridspec_kw={"width_ratios": [5, 1]},
    )

    sk.plot2d(
        w.normed_arbor, plane="xz",
        ax=ax_nodes, color_by="ntype", skel_cmap="Set2",
    )
    ax_nodes.set_xlabel('X (µm)')
    ax_nodes.set_ylabel('Z (µm)')
    ax_nodes.set_title('Warped and Normed Arbor')
    for y in (0, 12):
        ax_nodes.axhline(y, ls='--', c='k')
    ax_nodes.text(ax_nodes.get_xlim()[1], 0,  'ON SAC',
                  va='bottom', ha='right', fontsize=10)
    ax_nodes.text(ax_nodes.get_xlim()[1], 12, 'OFF SAC',
                  va='bottom', ha='right', fontsize=10)

    prof = w.normed_arbor.extra["z_profile"]
    ax_prof.plot(prof["z_dist"], prof["z_x"], lw=2)
    ax_prof.barh(prof["z_x"], prof["z_hist"], alpha=0.5)
    ax_prof.set_xlabel('dendritic length')
    ax_prof.set_title('Z-profile')
    ax_prof.axhline(0,  ls='--', c='k')
    ax_prof.axhline(12, ls='--', c='k')
    ax_prof.spines['top'].set_visible(False)
    ax_prof.spines['right'].set_visible(False)

    for ax in (ax_nodes, ax_prof):
        ax.set_aspect('auto')

    fig.tight_layout()
    fig.savefig(profile_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    if verbose:
        print("Warp and profile complete.")


# ---------- CLI entry-point ---------------------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Skeletonise and warp a retinal segment."
    )
    p.add_argument("seg_id", type=int, help="EM segment ID (integer).")
    p.add_argument(
        "--output-dir", type=Path, default=Path("./output"),
        help="Directory in which to store meshes, skeletons, and plots.",
    )
    p.add_argument(
        "--overwrite", action="store_true",
        help="Force re-running steps even if outputs are present.",
    )
    p.add_argument(
        "--no-verbose", dest="verbose", action="store_false",
        help="Run quietly.",
    )
    return p.parse_args()

def main() -> None:
    args = parse_args()
    outdir = args.output_dir / str(args.seg_id)
    outdir.mkdir(parents=True, exist_ok=True)

    mesh_path = fetch_mesh(args.seg_id, outdir, args.verbose, args.overwrite)
    skel_path = build_skeleton(mesh_path, outdir,
                               args.seg_id, args.verbose, args.overwrite)
    warp_and_profile(skel_path, outdir, args.verbose, args.overwrite)

if __name__ == "__main__":
    main()
