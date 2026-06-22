# Animation interactive de toutes les frames d'une simulation.
# Aucune dépendance hors numpy + matplotlib (lecture directe du PLY binaire).
#
# En 3D, l'axe VERTICAL du graphe est y (comme dans Matter) ; le sol est le plan x-z.
#
# Utilisation :
#   python3 postprocess/animate.py                      # sim "collapse", couleur = vitesse
#   python3 postprocess/animate.py avalanche            # sim donnée
#   python3 postprocess/animate.py avalanche q          # coloré par le champ "q"
#   python3 postprocess/animate.py avalanche top        # vue de dessus (plan x-z, "carte")
#   python3 postprocess/animate.py avalanche side       # vue de côté (plan x-y)
#   python3 postprocess/animate.py avalanche 90,-90     # vue perso : elevation,azimut
#   python3 postprocess/animate.py avalanche --every 10 # 1 point sur 10 (fluide / rapide)
#   python3 postprocess/animate.py avalanche save        # exporte un GIF au lieu d'afficher
#   (top/side/iso, "save", "elev,azim" et "--every N" se combinent dans n'importe quel ordre)

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# réutilise les fonctions de lecture déjà écrites
from view_frame import read_ply, find_sim_dir, speed

# presets de vue 3D : (elevation, azimut) en degres
VIEWS = {
    "top":  (90, -90),   # vue de dessus -> on voit le plan x-z (carte)
    "side": (0,  -90),   # vue de cote   -> on voit le plan x-y
    "iso":  (25, -60),   # vue isometrique (defaut matplotlib)
}


def main():
    args = sys.argv[1:]

    # extrait les options dans n'importe quel ordre
    save = "save" in args
    args = [a for a in args if a != "save"]

    every = 1  # n'afficher qu'1 point sur N (ne change pas la simulation)
    if "--every" in args:
        i = args.index("--every")
        every = max(1, int(args[i + 1]))
        del args[i:i + 2]

    view = None
    for a in list(args):
        if a in VIEWS:
            view = VIEWS[a]; args.remove(a)
        elif "," in a:  # "elev,azim"
            try:
                e, z = a.split(","); view = (float(e), float(z)); args.remove(a)
            except ValueError:
                pass

    sim   = args[0] if len(args) > 0 else "collapse"
    color = args[1] if len(args) > 1 else "speed"

    sim_dir = find_sim_dir(sim)

    # liste triée des frames disponibles (on ignore les fichiers vides/tronqués,
    # p.ex. ecriture interrompue par un disque plein)
    frames = []
    skipped = []
    for f in os.listdir(sim_dir):
        if not (f.startswith("particles_f") and f.endswith(".ply")):
            continue
        n = int(f.split("_f")[1].split(".")[0])
        if os.path.getsize(os.path.join(sim_dir, f)) == 0:
            skipped.append(n)
        else:
            frames.append(n)
    frames.sort()
    if skipped:
        print(f"Attention : {len(skipped)} frame(s) vide(s) ignorée(s) : "
              f"{sorted(skipped)}")
    if not frames:
        raise FileNotFoundError(f"Aucun particles_f*.ply non-vide dans {sim_dir}")

    fps = None
    info_path = os.path.join(sim_dir, "info.txt")
    if os.path.isfile(info_path):
        fps = float(np.loadtxt(info_path)[1])

    # détection automatique 2D / 3D sur la 1ère frame
    d0 = read_ply(os.path.join(sim_dir, f"particles_f{frames[0]}.ply"))
    is3d = "z" in d0

    def load(frame):
        d = read_ply(os.path.join(sim_dir, f"particles_f{frame}.ply"))
        c = speed(d) if color == "speed" else d[color]
        sl = slice(None, None, every)  # sous-echantillonnage de l'affichage
        if is3d:
            return d["x"][sl], d["y"][sl], d["z"][sl], c[sl]
        return d["x"][sl], d["y"][sl], None, c[sl]

    # bornes fixes (sur 1ère + dernière frame) pour que la vue ne saute pas
    f0 = load(frames[0])
    fL = load(frames[-1])
    xmin, xmax = min(f0[0].min(), fL[0].min()), max(f0[0].max(), fL[0].max())
    ymin, ymax = min(f0[1].min(), fL[1].min()), max(f0[1].max(), fL[1].max())
    cmax = max(f0[3].max(), fL[3].max()) or 1.0
    clabel = "|v| (m/s)" if color == "speed" else color

    if is3d:
        # axe vertical du graphe = y (physique) ; sol = plan x-z. On trace (x, z, y).
        zmin, zmax = min(f0[2].min(), fL[2].min()), max(f0[2].max(), fL[2].max())
        fig = plt.figure(figsize=(9, 7))
        ax = fig.add_subplot(111, projection="3d")
        sc = ax.scatter(f0[0], f0[2], f0[1], c=f0[3], cmap="jet",
                        s=4, marker=".", vmin=0, vmax=cmax)
        ax.set_xlim(xmin, xmax)   # x = aval
        ax.set_ylim(zmin, zmax)   # z = largeur
        ax.set_zlim(ymin, ymax)   # y = vertical
        ax.set_xlabel("x (m)  [aval]")
        ax.set_ylabel("z (m)  [largeur]")
        ax.set_zlabel("y (m)  [vertical]")
        try:
            ax.set_box_aspect((xmax - xmin, zmax - zmin, ymax - ymin))
        except Exception:
            pass
        ax.view_init(*(view if view else VIEWS["iso"]))
    else:
        fig, ax = plt.subplots(figsize=(9, 5))
        sc = ax.scatter(f0[0], f0[1], c=f0[3], cmap="jet",
                        s=4, marker=".", vmin=0, vmax=cmax)
        ax.set_aspect("equal")
        ax.set_xlim(xmin - 0.05, xmax + 0.05)
        ax.set_ylim(ymin - 0.05, ymax + 0.05)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")

    fig.colorbar(sc, ax=ax, label=clabel)
    title = ax.set_title("")

    def update(i):
        frame = frames[i]
        x, y, z, c = load(frame)
        if is3d:
            sc._offsets3d = (x, z, y)   # remap : sol = plan x-z, vertical = y
        else:
            sc.set_offsets(np.column_stack([x, y]))
        sc.set_array(c)
        t = f"  (t = {frame / fps:.2f} s)" if fps else ""
        title.set_text(f"{sim} — frame {frame}{t}")
        return sc, title

    anim = FuncAnimation(fig, update, frames=len(frames),
                         interval=120, blit=False, repeat=True)

    if save:
        out = os.path.join(sim_dir, f"{sim}_anim.gif")
        anim.save(out, writer="pillow", fps=8)
        print("Animation sauvegardée :", out)
    else:
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
