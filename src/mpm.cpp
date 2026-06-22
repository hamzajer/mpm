// Copyright (C) 2024 Lars Blatny. Released under GPL-3.0 license.

#include "tools.hpp"
#include "simulation/simulation.hpp"
#include "sampling/sampling_particles.hpp"

#include "objects/object_plate.hpp"
#include "objects/object_biplane.hpp"

int main(){

    Simulation sim;
    sim.initialize(/*save to file*/ true, /*path*/ "output/", /*name*/ "test_avalanche_2D");

    sim.save_grid   = true;
    sim.end_frame   = 80;    // 80 frames a 4 fps = 20 s simules
    sim.fps         = 4;
    sim.n_threads   = 8;
    sim.cfl         = 0.5;
    sim.flip_ratio  = -0.95; // AFLIP

    ////// ELASTICITE (neige molle)
    sim.elastic_model = ElasticModel::Hencky;
    sim.E   = 1e5;   // module d'Young (Pa) - neige molle
    sim.nu  = 0.3;   // coefficient de Poisson
    sim.rho = 60;   // densite poudreuse (kg/m3)

    ////// GRAVITE : verticale (c'est le terrain qui porte la pente)
    sim.gravity = TV::Zero();
    sim.gravity[1] = -9.81;

    ////// TERRAIN BI-PLAN
    T angle1 = 35.0, angle2 = 10.0;   // degres : pente amont, pente aval
    T Lslope1 = 200.0, Lslope2 = 200.0; // longueurs le long de chaque pente (m)
    T width   = 60.0;                  // largeur en z (m)
    T terrain_friction = 0.40;          // ~ tan(22 deg), friction neige/sol

    sim.objects.push_back(std::make_unique<ObjectBiplane>(
        BC::SlipFree, terrain_friction, angle1, angle2, Lslope1, Lslope2));

    // Optionnel : murs lateraux pour contenir l'ecoulement en z
    // sim.plates.push_back(std::make_unique<ObjectPlate>(0,     PlateType::back,  BC::SlipFree));
    // sim.plates.push_back(std::make_unique<ObjectPlate>(width, PlateType::front, BC::SlipFree));

    ////// PLAQUE DE NEIGE : 30 x 30 m (plan de pente) x 0.30 m d'epaisseur
    T slab_len   = 30.0;   // le long de la pente (x local)
    T slab_thick = 0.30;   // epaisseur (perpendiculaire a la pente)
    T slab_width = 30.0;   // largeur (z local)
    T k_rad      = 0.10;   // rayon d'echantillonnage (m) 

    sim.Lx = slab_len;
    sim.Ly = slab_thick;
    sim.Lz = slab_width;
    sampleParticles(sim, k_rad);   // echantillonne une boite [0,Lx]x[0,Ly]x[0,Lz]

    ////// PLACEMENT : centrer et poser la plaque sur la pente amont (35 deg)
    T a1 = angle1 * M_PI / 180.0;
    T c = std::cos(a1), s = std::sin(a1);
    T tan1 = std::tan(a1), tan2 = std::tan(angle2 * M_PI / 180.0);
    T x1   = Lslope1 * std::cos(a1);
    T Htop = Lslope1 * std::sin(a1) + Lslope2 * std::sin(angle2 * M_PI / 180.0);

    T s_center = 0.5 * Lslope1;          // milieu de la pente amont (le long de la pente)
    T x_c = s_center * c;                // centre horizontal de la plaque
    T y_c = Htop - tan1 * x_c;           // hauteur de la surface au centre
    T z_c = 0.5 * width;                 // centre en largeur
    T gap = 0.01;                        // petit jeu pour poser au-dessus de la surface

    for(int p = 0; p < sim.Np; p++){
        //position de la plaque (particules)
        T x_local = sim.particles.x[p](0);
        T y_local = sim.particles.x[p](1);
        T z_local = sim.particles.x[p](2);

        //recentre la position des particules 
        T u  = x_local - 0.5 * slab_len;   
        T nn = y_local + gap;              
        T w  = z_local - 0.5 * slab_width; 
        //on applique une rotation pour aligner la plaque avec la pente amont
        sim.particles.x[p](0) = x_c + u * c + nn * s;    // normale   = ( c, -s, 0)
        sim.particles.x[p](1) = y_c - u * s + nn * c;    // normale   = ( s,  c, 0)
        sim.particles.x[p](2) = z_c + w;
    }
    
    sim.grid_reference_point = TV(x_c, y_c, z_c);

    ////// PLASTICITE : Drucker-Prager (neige granulaire, faible cohesion)
    sim.plastic_model = PlasticModel::DP;
    sim.use_pradhana  = true;
    sim.q_prefac      = 1.0 / std::sqrt(2.0);
    sim.M             = std::tan(30.0 * M_PI / 180.0); 
    sim.q_cohesion    = 0;                             // poudreuse  sans cohesion

    sim.simulate();
    return 0;
}

