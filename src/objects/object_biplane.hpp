// Terrain bi-plan : pente amont (angle1) raccordée à une pente aval (angle2),
// invariant selon z (la largeur). Convention Matter : y vertical, x aval, z largeur.
//
//   y
//   |\
//   |  \  (angle1, longueur L1 le long de la pente)
//   |    \____
//   |          \___  (angle2, longueur L2 le long de la pente)
//   |______________\_____ x
//
// Le sol est l'ensemble des points sous la surface y = height(x).

#ifndef OBJECTBIPLANE_HPP
#define OBJECTBIPLANE_HPP

#include "object_general.hpp"

class ObjectBiplane : public ObjectGeneral {
public:
    T a1, a2;     // angles (radians) des pentes amont et aval
    T L1, L2;     // longueurs le long de la pente (m)
    T x1;         // abscisse horizontale de la rupture de pente
    T Htop;       // hauteur du sommet (pour que le bas soit a y = 0)

    ~ObjectBiplane(){}

    ObjectBiplane(BC bc_in, T friction_in,
                  T angle1_deg = 35.0, T angle2_deg = 10.0,
                  T L1_in = 200.0, T L2_in = 200.0,
                  std::string name_in = "biplane", bool force_calc_in = false)
        : ObjectGeneral(bc_in, friction_in, name_in, force_calc_in),
          L1(L1_in), L2(L2_in) {
        a1 = angle1_deg * M_PI / 180.0;
        a2 = angle2_deg * M_PI / 180.0;
        x1   = L1 * std::cos(a1);                       // rupture de pente (horizontal)
        Htop = L1 * std::sin(a1) + L2 * std::sin(a2);   // sommet -> bas a y=0
    }

    // Hauteur de la surface au point horizontal x
    T height(T x) const {
        if (x <= x1)
            return Htop - std::tan(a1) * x;
        else
            return (Htop - std::tan(a1) * x1) - std::tan(a2) * (x - x1);
    }

    bool inside(const TV& X_in) const override {
        return X_in(1) < height(X_in(0));   // sous la surface = dans le sol
    }

    TV normal(const TV& X_in) const override {
        T slope = (X_in(0) <= x1) ? std::tan(a1) : std::tan(a2);
        TV n;
        n(0) = slope;   // = -d(height)/dx
        n(1) = 1.0;
        n(2) = 0.0;
        return n.normalized();
    }
};

#endif  // OBJECTBIPLANE_HPP
