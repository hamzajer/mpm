# Fenêtre interactive (zoom/pan) d'une frame de particules.
# Aucune dépendance hors numpy + matplotlib : le PLY binaire est lu directement.
#
# Utilisation :
#   python3 postprocess/view_frame.py                 # frame 0 de output/collapse
#   python3 postprocess/view_frame.py 10              # frame 10
#   python3 postprocess/view_frame.py 10 collapse     # frame 10, sim "collapse"
#   python3 postprocess/view_frame.py 10 collapse q   # coloré par le champ "q"

import os
import sys
import numpy as np
import matplotlib.pyplot as plt


def read_ply(path):
    """Lit un PLY binaire little-endian (tous champs en double) -> dict de tableaux."""
    with open(path, "rb") as f:
        # --- entête ASCII ---
        names, count = [], 0
        line = f.readline().decode("ascii", "ignore").strip()
        assert line == "ply", f"{path} n'est pas un fichier PLY"
        while True:
            line = f.readline().decode("ascii", "ignore").strip()
            if line.startswith("element vertex"):
                count = int(line.split()[-1])
            elif line.startswith("property"):
                names.append(line.split()[-1])
            elif line == "end_header":
                break
        # --- bloc binaire : count lignes de len(names) doubles ---
        dtype = np.dtype([(n, "<f8") for n in names])
        data = np.fromfile(f, dtype=dtype, count=count)
    return {n: data[n] for n in names}


def speed(d):
    """Norme de la vitesse à partir des composantes présentes (2D ou 3D)."""
    comps = [d[k] for k in ("vx", "vy", "vz") if k in d]
    return np.sqrt(sum(c ** 2 for c in comps))


def find_sim_dir(sim_name):
    """Trouve le dossier de sortie, qu'on lance depuis matter/ ou depuis build/."""
    here = os.path.dirname(os.path.abspath(__file__))      # .../matter/postprocess
    root = os.path.dirname(here)                            # .../matter
    candidates = [
        os.path.join(root, "build", "output", sim_name),
        os.path.join(root, "output", sim_name),
        os.path.join(os.getcwd(), "output", sim_name),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise FileNotFoundError(
        "Dossier de sortie introuvable. Cherché :\n  " + "\n  ".join(candidates)
    )


def main():
    frame = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    sim   = sys.argv[2] if len(sys.argv) > 2 else "collapse"
    color = sys.argv[3] if len(sys.argv) > 3 else "speed"  # speed | p | q | ...

    sim_dir = find_sim_dir(sim)
    ply_path = os.path.join(sim_dir, f"particles_f{frame}.ply")
    if not os.path.isfile(ply_path):
        raise FileNotFoundError(ply_path)

    d = read_ply(ply_path)
    is3d = "z" in d   # détection automatique 2D / 3D

    # temps de la frame (info.txt : ligne 2 = fps)
    t = None
    info_path = os.path.join(sim_dir, "info.txt")
    if os.path.isfile(info_path):
        info = np.loadtxt(info_path)
        t = frame / float(info[1])

    if color == "speed":
        c = speed(d)
        clabel = "|v| (m/s)"
    else:
        c = d[color]
        clabel = color
    print(f"Frame {frame} : {len(d['x'])} particules ({'3D' if is3d else '2D'}), "
          f"{clabel} dans [{c.min():.3g}, {c.max():.3g}]")

    title = f"{sim} — frame {frame}"
    if t is not None:
        title += f"  (t = {t:.2f} s)"

    if is3d:
        fig = plt.figure(figsize=(8, 7))
        ax = fig.add_subplot(111, projection="3d")
        sc = ax.scatter(d["x"], d["y"], d["z"], c=c, cmap="jet", s=4, marker=".")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_zlabel("z (m)")
        try:
            ax.set_box_aspect((np.ptp(d["x"]), np.ptp(d["y"]), np.ptp(d["z"])))
        except Exception:
            pass
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        sc = ax.scatter(d["x"], d["y"], c=c, cmap="jet", s=4, marker=".")
        ax.set_aspect("equal")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")

    fig.colorbar(sc, ax=ax, label=clabel)
    ax.set_title(title)
    plt.tight_layout()
    plt.show()   # fenêtre interactive : zoom/pan en 2D, rotation en 3D


if __name__ == "__main__":
    main()
