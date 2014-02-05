#!/usr/bin/env python2.7
import math
import numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import subprocess
import vtk

numpy.seterr(all='warn', over='raise')

# Sphere version number. This field should correspond to the value in
# `../src/constants.h`.
VERSION=1.0

class Spherebin:
    '''
    Class containing all ``sphere`` data.

    Contains functions for reading and writing binaries, as well as simulation
    setup and data analysis. Most arrays are initialized to default values.

    :param np: The number of particles to allocate memory for (default = 1)
    :type np: int
    :param nd: The number of spatial dimensions (default = 3). Note that 2D and
        1D simulations currently are not possible.
    :type nd: int
    :param nw: The number of dynamic walls (default = 1)
    :type nw: int
    :param sid: The simulation id (default = 'unnamed'). The simulation files
        will be written with this base name.
    :type sid: str
    :param fluid: Setup fluid simulation (default = False)
    :type fluid: bool
    '''

    def __init__(self, np = 1, nd = 3, nw = 1, sid = 'unnamed', fluid = False):

        # Sphere version number
        self.version = numpy.ones(1, dtype=numpy.float64)*VERSION

        # The number of spatial dimensions. Values other that 3 do not work
        self.nd = numpy.ones(1, dtype=numpy.int32)*nd

        # The number of particles
        self.np = numpy.ones(1, dtype=numpy.uint32)*np

        # The simulation id (text string)
        self.sid = sid

        ## Time parameters
        # Computational time step length [s]
        self.time_dt         = numpy.zeros(1, dtype=numpy.float64)

        # Current time [s]
        self.time_current    = numpy.zeros(1, dtype=numpy.float64)

        # Total time [s]
        self.time_total      = numpy.zeros(1, dtype=numpy.float64)

        # File output interval [s]
        self.time_file_dt    = numpy.zeros(1, dtype=numpy.float64)

        # The number of files written
        self.time_step_count = numpy.zeros(1, dtype=numpy.uint32)

        ## World dimensions and grid data
        # The Euclidean coordinate to the origo of the sorting grid
        self.origo   = numpy.zeros(self.nd, dtype=numpy.float64)

        # The sorting grid size (x,y,z)
        self.L       = numpy.zeros(self.nd, dtype=numpy.float64)

        # The number of sorting cells in each dimension
        self.num     = numpy.zeros(self.nd, dtype=numpy.uint32)

        # Whether to treat the lateral boundaries as periodic (1) or not (0)
        self.periodic = numpy.zeros(1, dtype=numpy.uint32)

        ## Particle data
        # Particle position vectors [m]
        self.x       = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # Particle radii [m]
        self.radius  = numpy.ones(self.np, dtype=numpy.float64)

        # The sums of x and y movement [m]
        self.xysum   = numpy.zeros((self.np, 2), dtype=numpy.float64)

        # The linear velocities [m/s]
        self.vel     = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # Fix the particle horizontal velocities? 0: No, 1: Yes
        self.fixvel  = numpy.zeros(self.np, dtype=numpy.float64)

        # The linear force vectors [N]
        self.force   = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # The angular position vectors [rad]
        self.angpos  = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # The angular velocity vectors [rad/s]
        self.angvel  = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # The torque vectors [N*m]
        self.torque  = numpy.zeros((self.np, self.nd), dtype=numpy.float64)

        # The shear friction energy dissipation rates [W]
        self.es_dot  = numpy.zeros(self.np, dtype=numpy.float64)

        # The total shear energy dissipations [J]
        self.es      = numpy.zeros(self.np, dtype=numpy.float64)

        # The viscous energy dissipation rates [W]
        self.ev_dot  = numpy.zeros(self.np, dtype=numpy.float64)

        # The total viscois energy dissipation [J]
        self.ev      = numpy.zeros(self.np, dtype=numpy.float64)

        # The total particle pressures [Pa]
        self.p       = numpy.zeros(self.np, dtype=numpy.float64)

        # The gravitational acceleration vector [N*m/s]
        self.g        = numpy.array([0.0, 0.0, 0.0], dtype=numpy.float64)

        # The Hookean coefficient for elastic stiffness normal to the contacts
        # [N/m]
        self.k_n      = numpy.ones(1, dtype=numpy.float64) * 1.16e9

        # The Hookean coefficient for elastic stiffness tangential to the
        # contacts [N/m]
        self.k_t      = numpy.ones(1, dtype=numpy.float64) * 1.16e9

        # The Hookean coefficient for elastic stiffness opposite of contact
        # rotations. UNUSED
        self.k_r      = numpy.zeros(1, dtype=numpy.float64)

        # The viscosity normal to the contact [N/(m/s)]
        self.gamma_n  = numpy.zeros(1, dtype=numpy.float64)

        # The viscosity tangential to the contact [N/(m/s)]
        self.gamma_t  = numpy.zeros(1, dtype=numpy.float64)

        # The viscosity to contact rotation [N/(m/s)]
        self.gamma_r  = numpy.zeros(1, dtype=numpy.float64)

        # The coefficient of static friction on the contact [-]
        self.mu_s     = numpy.ones(1, dtype=numpy.float64)

        # The coefficient of dynamic friction on the contact [-]
        self.mu_d     = numpy.ones(1, dtype=numpy.float64)

        # The coefficient of rotational friction on the contact [-]
        self.mu_r     = numpy.zeros(1, dtype=numpy.float64)

        # The viscosity normal to the walls [N/(m/s)]
        self.gamma_wn = numpy.ones(1, dtype=numpy.float64) * 1.0e3

        # The viscosity tangential to the walls [N/(m/s)]
        self.gamma_wt = numpy.ones(1, dtype=numpy.float64) * 1.0e3

        # The coeffient of static friction of the walls [-]
        self.mu_ws    = numpy.ones(1, dtype=numpy.float64)

        # The coeffient of dynamic friction of the walls [-]
        self.mu_wd    = numpy.ones(1, dtype=numpy.float64)

        # The particle density [kg/(m^3)]
        self.rho      = numpy.ones(1, dtype=numpy.float64) * 2600.0

        # The contact model to use
        # 1: Normal: elasto-viscous, tangential: visco-frictional
        # 2: Normal: elasto-viscous, tangential: elasto-visco-frictional
        self.contactmodel = numpy.ones(1, dtype=numpy.uint32) * 2 # lin-visc-el

        # Capillary bond prefactor
        self.kappa        = numpy.zeros(1, dtype=numpy.float64)

        # Capillary bond debonding distance [m]
        self.db           = numpy.zeros(1, dtype=numpy.float64)

        # Capillary bond liquid volume [m^3]
        self.V_b          = numpy.zeros(1, dtype=numpy.float64)

        ## Wall data
        # Number of dynamic walls
        # nw = 1: Uniaxial
        # nw = 2: Biaxial
        # nw = 5: Triaxial
        self.nw      = numpy.ones(1, dtype=numpy.uint32) * nw

        # Wall modes
        # 0: Fixed, 1: Normal stress condition, 2: Normal velocity condition
        self.wmode   = numpy.zeros(self.nw, dtype=numpy.int32)

        # Wall normals
        self.w_n     = numpy.zeros((self.nw, self.nd), dtype=numpy.float64)
        if (self.nw >= 1):
            self.w_n[0,2] = -1.0
        if (self.nw >= 2):
            self.w_n[1,0] = -1.0
        if (self.nw >= 3):
            self.w_n[2,0] =  1.0
        if (self.nw >= 4):
            self.w_n[3,1] = -1.0
        if (self.nw >= 5):
            self.w_n[4,1] =  1.0
            
        # Wall positions on the axes that are parallel to the wall normal [m]
        self.w_x     = numpy.ones(self.nw, dtype=numpy.float64)

        # Wall masses [kg]
        self.w_m     = numpy.zeros(self.nw, dtype=numpy.float64)

        # Wall velocities on the axes that are parallel to the wall normal [m/s]
        self.w_vel   = numpy.zeros(self.nw, dtype=numpy.float64)

        # Wall forces on the axes that are parallel to the wall normal [m/s]
        self.w_force = numpy.zeros(self.nw, dtype=numpy.float64)

        # Wall stress on the axes that are parallel to the wall normal [Pa]
        self.w_devs  = numpy.zeros(self.nw, dtype=numpy.float64)

        # Wall stress modulation amplitude [Pa]
        self.w_devs_A = numpy.zeros(1, dtype=numpy.float64)

        # Wall stress modulation frequency [Hz]
        self.w_devs_f = numpy.zeros(1, dtype=numpy.float64)

        ## Bond parameters
        # Radius multiplier to the parallel-bond radii
        self.lambda_bar = numpy.ones(1, dtype=numpy.float64)

        # Number of bonds
        self.nb0 = numpy.zeros(1, dtype=numpy.uint32)

        # Bond tensile strength [Pa]
        self.sigma_b = numpy.ones(1, dtype=numpy.uint32) * numpy.infty

        # Bond shear strength [Pa]
        self.tau_b = numpy.ones(1, dtype=numpy.uint32) * numpy.infty

        # Bond pairs
        self.bonds = numpy.zeros((self.nb0, 2), dtype=numpy.uint32)

        # Parallel bond movement
        self.bonds_delta_n = numpy.zeros(self.nb0, dtype=numpy.float64)

        # Shear bond movement
        self.bonds_delta_t = numpy.zeros((self.nb0, self.nd),
                                         dtype=numpy.float64)

        # Twisting bond movement
        self.bonds_omega_n = numpy.zeros(self.nb0, dtype=numpy.float64)

        # Bending bond movement
        self.bonds_omega_t = numpy.zeros((self.nb0, self.nd),
                                         dtype=numpy.float64)

        ## Fluid parameters

        # Simulate fluid? True: Yes, False: no
        self.fluid = fluid

        if (self.fluid == True):
            # Fluid dynamic viscosity [N/(m/s)]
            self.nu = numpy.zeros(1, dtype=numpy.float64)

            # Fluid velocities [m/s]
            self.v_f = numpy.zeros(
                (self.num[0], self.num[1], self.num[2], self.nd),
                dtype=numpy.float64)

            # Fluid pressures [Pa]
            self.p_f = numpy.zeros((self.num[0], self.num[1], self.num[2]),
                                   dtype=numpy.float64)

            # Fluid cell porosities [-]
            self.phi = numpy.zeros((self.num[0], self.num[1], self.num[2]),
                                   dtype=numpy.float64)

            # Fluid cell porosity change [1/s]
            self.dphi = numpy.zeros((self.num[0], self.num[1], self.num[2]),
                                   dtype=numpy.float64)

            # Fluid density [kg/(m^3)]
            self.rho_f = numpy.ones(1, dtype=numpy.float64) * 1.0e3

            # Pressure modulation at the top boundary
            self.p_mod_A = numpy.zeros(1, dtype=numpy.float64)  # Amplitude [Pa]
            self.p_mod_f = numpy.zeros(1, dtype=numpy.float64)  # Frequency [Hz]
            self.p_mod_phi = numpy.zeros(1, dtype=numpy.float64) # Shift [rad]

            # Boundary conditions at the top and bottom of the fluid grid
            # 0: Dirichlet, 1: Neumann
            self.bc_bot = numpy.zeros(1, dtype=numpy.int32)
            self.bc_top = numpy.zeros(1, dtype=numpy.int32)
            # Free slip boundaries? 1: yes
            self.free_slip_bot = numpy.ones(1, dtype=numpy.int32)
            self.free_slip_top = numpy.ones(1, dtype=numpy.int32)

    def __cmp__(self, other):
        '''
        Called when to Spherebin objects are compared. Returns 0 if the values
        are identical.
        TODO: Replace print(#) with print("field name")
        '''
        if (self.version != other.version):
            print(1)
            return 1
        elif (self.nd != other.nd):
            print(2)
            return 2
        elif (self.np != other.np):
            print(4)
            return 4
        elif (self.time_dt != other.time_dt):
            print(5)
            return 5
        elif (self.time_current != other.time_current):
            print(6)
            return 6
        elif (self.time_total != other.time_total):
            print(7)
            return 7
        elif (self.time_file_dt != other.time_file_dt):
            print(8)
            return 8
        elif (self.time_step_count != other.time_step_count):
            print(9)
            return 9
        elif ((self.origo != other.origo).any()):
            print(10)
            return 10
        elif ((self.L != other.L).any()):
            print(11)
            return 11
        elif ((self.num != other.num).any()):
            print(12)
            return 12
        elif (self.periodic != other.periodic):
            print(13)
            return 13
        elif ((self.x != other.x).any()):
            print(14)
            return 14
        elif ((self.radius != other.radius).any()):
            print(15)
            return 15
        elif ((self.xysum != other.xysum).any()):
            print(16)
            return 16
        elif ((self.vel != other.vel).any()):
            print(17)
            return 17
        elif ((self.fixvel != other.fixvel).any()):
            print(18)
            return 18
        elif ((self.force != other.force).any()):
            print(19)
            return 19
        elif ((self.angpos != other.angpos).any()):
            print(20)
            return 20
        elif ((self.angvel != other.angvel).any()):
            print(21)
            return 21
        elif ((self.torque != other.torque).any()):
            print(22)
            return 22
        elif ((self.es_dot != other.es_dot).any()):
            print(23)
            return 23
        elif ((self.es != other.es).any()):
            print(24)
            return 24
        elif ((self.ev_dot != other.ev_dot).any()):
            print(25)
            return 25
        elif ((self.ev != other.ev).any()):
            print(26)
            return 26
        elif ((self.p != other.p).any()):
            print(27)
            return 27
        elif ((self.g != other.g).any()):
            print(28)
            return 28
        elif (self.k_n != other.k_n):
            print(29)
            return 29
        elif (self.k_t != other.k_t):
            print(30)
            return 30
        elif (self.k_r != other.k_r):
            print(31)
            return 31
        elif (self.gamma_n != other.gamma_n):
            print(32)
            return 32
        elif (self.gamma_t != other.gamma_t):
            print(33)
            return 33
        elif (self.gamma_r != other.gamma_r):
            print(34)
            return 34
        elif (self.mu_s != other.mu_s):
            print(35)
            return 35
        elif (self.mu_d != other.mu_d):
            print(36)
            return 36
        elif (self.mu_r != other.mu_r):
            print(37)
            return 37
        elif (self.rho != other.rho):
            print(38)
            return 38
        elif (self.contactmodel != other.contactmodel):
            print(39)
            return 39
        elif (self.kappa != other.kappa):
            print(40)
            return 40
        elif (self.db != other.db):
            print(41)
            return 41
        elif (self.V_b != other.V_b):
            print(42)
            return 42
        elif (self.nw != other.nw):
            print(43)
            return 43
        elif ((self.wmode != other.wmode).any()):
            print(44)
            return 44
        elif ((self.w_n != other.w_n).any()):
            print(45)
            return 45
        elif ((self.w_x != other.w_x).any()):
            print(46)
            return 46
        elif ((self.w_m != other.w_m).any()):
            print(47)
            return 47
        elif ((self.w_vel != other.w_vel).any()):
            print(48)
            return 48
        elif ((self.w_force != other.w_force).any()):
            print(49)
            return 49
        elif ((self.w_devs != other.w_devs).any()):
            print(50)
            return 50
        elif (self.w_devs_A != other.w_devs_A):
            print(51)
            return 51
        elif (self.w_devs_f != other.w_devs_f):
            print(52)
            return 52
        elif (self.gamma_wn != other.gamma_wn):
            print(53)
            return 53
        elif (self.gamma_wt != other.gamma_wt):
            print(54)
            return 54
        elif (self.lambda_bar != other.lambda_bar):
            print(55)
            return 55
        elif (self.nb0 != other.nb0):
            print(56)
            return 56
        elif (self.sigma_b != other.sigma_b):
            print(57)
            return 57
        elif (self.tau_b != other.tau_b):
            print(58)
            return 58
        elif (self.bonds != other.bonds):
            print(59)
            return 59
        elif (self.bonds_delta_n != other.bonds_delta_n):
            print(60)
            return 60
        elif (self.bonds_delta_t != other.bonds_delta_t):
            print(61)
            return 61
        elif (self.bonds_omega_n != other.bonds_omega_n):
            print(62)
            return 62
        elif (self.bonds_omega_t != other.bonds_omega_t):
            print(63)
            return 63
        elif (self.fluid != other.fluid):
            print(64)
            return 64

        if (self.fluid == True):
            if (self.nu != other.nu):
                print(65)
                return 65
            elif ((self.v_f != other.v_f).any()):
                print(66)
                return 66
            elif ((self.p_f != other.p_f).any()):
                print(67)
                return 67
            elif ((self.phi != other.phi).any()):
                print(68)
                return 68
            elif ((self.dphi != other.dphi).any()):
                print(69)
                return 69
            elif (self.rho_f != other.rho_f):
                print(70)
                return 70
            elif (self.p_mod_A != other.p_mod_A):
                print(71)
                return 71
            elif (self.p_mod_f != other.p_mod_f):
                print(72)
                return 72
            elif (self.p_mod_phi != other.p_mod_phi):
                print(73)
                return 73
            elif (self.bc_bot != other.bc_bot):
                print(74)
                return 74
            elif (self.bc_top != other.bc_top):
                print(75)
                return 75
            elif (self.free_slip_bot != other.free_slip_bot):
                print(76)
                return 76
            elif (self.free_slip_top != other.free_slip_top):
                print(77)
                return 77

        # All equal
        return 0

    def addParticle(self,
            x,
            radius,
            xysum = numpy.zeros(2),
            vel = numpy.zeros(3),
            fixvel = numpy.zeros(1),
            force = numpy.zeros(3),
            angpos = numpy.zeros(3),
            angvel = numpy.zeros(3),
            torque = numpy.zeros(3),
            es_dot = numpy.zeros(1),
            es = numpy.zeros(1),
            ev_dot = numpy.zeros(1),
            ev = numpy.zeros(1),
            p = numpy.zeros(1)):
        '''
        Add a single particle to the simulation object. The only required
        parameters are the position (x) and the radius (radius).

        :param x: A vector pointing to the particle center coordinate.
        :type x: numpy.array
        :param radius: The particle radius
        :type radius: float
        :param vel: The particle linear velocity (default = [0,0,0])
        :type vel: numpy.array
        :param fixvel: Fix horizontal linear velocity (0: No, 1: Yes, default=0)
        :type fixvel: float
        :param angpos: The particle angular position (default = [0,0,0])
        :type angpos: numpy.array
        :param angvel: The particle angular velocity (default = [0,0,0])
        :type angvel: numpy.array
        :param torque: The particle torque (default = [0,0,0])
        :type torque: numpy.array
        :param es_dot: The particle shear energy loss rate (default = 0)
        :type es_dot: float
        :param es: The particle shear energy loss (default = 0)
        :type es: float
        :param ev_dot: The particle viscous energy rate loss (default = 0)
        :type ev_dot: float
        :param ev: The particle viscous energy loss (default = 0)
        :type ev: float
        :param p: The particle pressure (default = 0)
        :type p: float
        '''

        self.np = self.np + 1

        self.x      = numpy.append(self.x, [x], axis=0)
        self.radius = numpy.append(self.radius, radius)
        self.vel    = numpy.append(self.vel, [vel], axis=0)
        self.xysum  = numpy.append(self.xysum, [xysum], axis=0)
        self.fixvel = numpy.append(self.fixvel, fixvel)
        self.force  = numpy.append(self.force, [force], axis=0)
        self.angpos = numpy.append(self.angpos, [angpos], axis=0)
        self.angvel = numpy.append(self.angvel, [angvel], axis=0)
        self.torque = numpy.append(self.torque, [torque], axis=0)
        self.es_dot = numpy.append(self.es_dot, es_dot)
        self.es     = numpy.append(self.es, es)
        self.ev_dot = numpy.append(self.ev_dot, ev_dot)
        self.ev     = numpy.append(self.ev, ev)
        self.p      = numpy.append(self.p, p) 

    def readbin(self, targetbin, verbose = True, bonds = True, devsmod = True,
            esysparticle = False):
        '''
        Reads a target ``sphere`` binary file.

        See also :func:`writebin()`, :func:`readfirst()`, :func:`readlast()`,
        :func:`readsecond`, and :func:`readstep`.

        :param targetbin: The path to the binary ``sphere`` file
        :type targetbin: str
        :param verbose: Show diagnostic information (default = True)
        :type verbose: bool
        :param bonds: The input file contains bond information (default = True).
            This parameter should be true for all recent ``sphere`` versions.
        :type bonds: bool
        :param devsmod: The input file contains information about modulating
            stresses at the top wall (default = True). This parameter should be
            true for all recent ``sphere`` versions.
        :type devsmod: bool
        :param esysparticle: Stop reading the file after reading the kinematics,
            which is useful for reading output files from other DEM programs.
            (default = False)
        :type esysparticle: bool
        '''

        fh = None
        try :
            if (verbose == True):
                print("Input file: {0}".format(targetbin))
            fh = open(targetbin, "rb")

            # Read the file version
            self.version = numpy.fromfile(fh, dtype=numpy.float64, count=1)

            # Read the number of dimensions and particles
            self.nd = numpy.fromfile(fh, dtype=numpy.int32, count=1)
            self.np = numpy.fromfile(fh, dtype=numpy.uint32, count=1)

            # Read the time variables
            self.time_dt = \
                    numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.time_current =\
                    numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.time_total =\
                    numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.time_file_dt =\
                    numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.time_step_count =\
                    numpy.fromfile(fh, dtype=numpy.uint32, count=1)

            # Allocate array memory for particles
            self.x       = numpy.empty((self.np, self.nd), dtype=numpy.float64)
            self.radius  = numpy.empty(self.np, dtype=numpy.float64)
            self.xysum   = numpy.empty((self.np, 2), dtype=numpy.float64)
            self.vel     = numpy.empty((self.np, self.nd), dtype=numpy.float64)
            self.fixvel  = numpy.empty(self.np, dtype=numpy.float64)
            self.es_dot  = numpy.empty(self.np, dtype=numpy.float64)
            self.es      = numpy.empty(self.np, dtype=numpy.float64)
            self.ev_dot  = numpy.empty(self.np, dtype=numpy.float64)
            self.ev      = numpy.empty(self.np, dtype=numpy.float64)
            self.p       = numpy.empty(self.np, dtype=numpy.float64)

            # Read remaining data from binary
            self.origo = numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
            self.L = numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
            self.num = numpy.fromfile(fh, dtype=numpy.uint32, count=self.nd)
            self.periodic = numpy.fromfile(fh, dtype=numpy.int32, count=1)

            # Per-particle vectors
            for i in range(self.np):
                self.x[i,:] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
                self.radius[i] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=1)

            self.xysum = numpy.fromfile(fh, dtype=numpy.float64,\
                    count=self.np*2).reshape(self.np,2)

            for i in range(self.np):
                self.vel[i,:] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
                self.fixvel[i] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=1)

            self.force = numpy.fromfile(fh, dtype=numpy.float64,\
                    count=self.np*self.nd).reshape(self.np, self.nd)

            self.angpos = numpy.fromfile(fh, dtype=numpy.float64,\
                    count=self.np*self.nd).reshape(self.np, self.nd)
            self.angvel = numpy.fromfile(fh, dtype=numpy.float64,\
                    count=self.np*self.nd).reshape(self.np, self.nd)
            self.torque = numpy.fromfile(fh, dtype=numpy.float64,\
                    count=self.np*self.nd).reshape(self.np, self.nd)

            if (esysparticle == True):
                return

            # Per-particle single-value parameters
            self.es_dot = numpy.fromfile(fh, dtype=numpy.float64, count=self.np)
            self.es     = numpy.fromfile(fh, dtype=numpy.float64, count=self.np)
            self.ev_dot = numpy.fromfile(fh, dtype=numpy.float64, count=self.np)
            self.ev     = numpy.fromfile(fh, dtype=numpy.float64, count=self.np)
            self.p      = numpy.fromfile(fh, dtype=numpy.float64, count=self.np)

            # Constant, global physical parameters
            self.g      = numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
            self.k_n          = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.k_t          = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.k_r          = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.gamma_n      = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.gamma_t      = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.gamma_r      = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.mu_s         = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.mu_d         = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.mu_r         = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.gamma_wn     = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.gamma_wt     = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.mu_ws        = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.mu_wd        = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.rho          = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.contactmodel = numpy.fromfile(fh, dtype=numpy.uint32, count=1)
            self.kappa        = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.db           = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            self.V_b          = numpy.fromfile(fh, dtype=numpy.float64, count=1)

            # Wall data
            self.nw      = numpy.fromfile(fh, dtype=numpy.uint32, count=1)
            self.wmode   = numpy.empty(self.nw, dtype=numpy.int32)
            self.w_n     = numpy.empty(self.nw*self.nd, dtype=numpy.float64)\
                    .reshape(self.nw,self.nd)
            self.w_x     = numpy.empty(self.nw, dtype=numpy.float64)
            self.w_m     = numpy.empty(self.nw, dtype=numpy.float64)
            self.w_vel   = numpy.empty(self.nw, dtype=numpy.float64)
            self.w_force = numpy.empty(self.nw, dtype=numpy.float64)
            self.w_devs  = numpy.empty(self.nw, dtype=numpy.float64)

            self.wmode   = numpy.fromfile(fh, dtype=numpy.int32, count=self.nw)
            for i in range(self.nw):
                self.w_n[i,:] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=self.nd)
                self.w_x[i]   = numpy.fromfile(fh, dtype=numpy.float64, count=1)
            for i in range(self.nw):
                self.w_m[i]   = numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.w_vel[i] = numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.w_force[i] =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.w_devs[i]= numpy.fromfile(fh, dtype=numpy.float64, count=1)
            if (devsmod == True):
                self.w_devs_A = numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.w_devs_f = numpy.fromfile(fh, dtype=numpy.float64, count=1)

            if (bonds == True):
                # Inter-particle bonds
                self.lambda_bar =\
                        numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.nb0 = numpy.fromfile(fh, dtype=numpy.uint32, count=1)
                self.sigma_b = numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.tau_b = numpy.fromfile(fh, dtype=numpy.float64, count=1)
                self.bonds = numpy.empty((self.nb0, 2), dtype=numpy.uint32)
                for i in range(self.nb0):
                    self.bonds[i,0] = numpy.fromfile(fh, dtype=numpy.uint32,
                            count=1)
                    self.bonds[i,1] = numpy.fromfile(fh, dtype=numpy.uint32,
                            count=1)
                self.bonds_delta_n = numpy.fromfile(fh, dtype=numpy.float64,
                        count=self.nb0)
                self.bonds_delta_t = numpy.fromfile(fh, dtype=numpy.float64,
                        count=self.nb0*self.nd).reshape(self.nb0, self.nd)
                self.bonds_omega_n = numpy.fromfile(fh, dtype=numpy.float64,
                        count=self.nb0)
                self.bonds_omega_t = numpy.fromfile(fh, dtype=numpy.float64,
                        count=self.nb0*self.nd).reshape(self.nb0, self.nd)
            else:
                self.nb0 = numpy.zeros(1, dtype=numpy.uint32)

            if (self.fluid == True):
                self.nu = numpy.fromfile(fh, dtype=numpy.float64, count=1)

                self.v_f = numpy.empty(
                        (self.num[0], self.num[1], self.num[2], self.nd),
                        dtype=numpy.float64)
                self.p_f = \
                        numpy.empty((self.num[0],self.num[1],self.num[2]),
                        dtype=numpy.float64)
                self.phi = \
                        numpy.empty((self.num[0],self.num[1],self.num[2]),
                        dtype=numpy.float64)
                self.dphi = \
                        numpy.empty((self.num[0],self.num[1],self.num[2]),
                        dtype=numpy.float64)

                for z in range(self.num[2]):
                    for y in range(self.num[1]):
                        for x in range(self.num[0]):
                            self.v_f[x,y,z,0] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)
                            self.v_f[x,y,z,1] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)
                            self.v_f[x,y,z,2] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)
                            self.p_f[x,y,z] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)
                            self.phi[x,y,z] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)
                            self.dphi[x,y,z] = \
                                    numpy.fromfile(fh, dtype=numpy.float64,\
                                    count=1)

                if (self.version >= 0.36):
                    self.rho_f =\
                            numpy.fromfile(fh, dtype=numpy.float64, count=1)
                    self.p_mod_A =\
                            numpy.fromfile(fh, dtype=numpy.float64, count=1)
                    self.p_mod_f =\
                            numpy.fromfile(fh, dtype=numpy.float64, count=1)
                    self.p_mod_phi =\
                            numpy.fromfile(fh, dtype=numpy.float64, count=1)

                    self.bc_bot =\
                            numpy.fromfile(fh, dtype=numpy.int32, count=1)
                    self.bc_top =\
                            numpy.fromfile(fh, dtype=numpy.int32, count=1)
                    self.free_slip_bot =\
                            numpy.fromfile(fh, dtype=numpy.int32, count=1)
                    self.free_slip_top =\
                            numpy.fromfile(fh, dtype=numpy.int32, count=1)


        finally:
            if fh is not None:
                fh.close()

    def writebin(self, folder = "../input/", verbose = True):
        '''
        Writes a ``sphere`` binary file to the ``../input/`` folder by default. The
        file name will be in the format ``<self.sid>.bin``.

        See also :func:`readbin()`.

        :param folder: The folder where to place the output binary file
        :type folder: str
        :param verbose: Show diagnostic information (default = True)
        :type verbose: bool
        '''

        fh = None
        try :
            targetbin = folder + "/" + self.sid + ".bin"
            if (verbose == True):
                print("Output file: {0}".format(targetbin))

            fh = open(targetbin, "wb")

            # Write the current version number
            fh.write(self.version.astype(numpy.float64))

            # Write the number of dimensions and particles
            fh.write(self.nd.astype(numpy.int32))
            fh.write(self.np.astype(numpy.uint32))

            # Write the time variables
            fh.write(self.time_dt.astype(numpy.float64))
            fh.write(self.time_current.astype(numpy.float64))
            fh.write(self.time_total.astype(numpy.float64))
            fh.write(self.time_file_dt.astype(numpy.float64))
            fh.write(self.time_step_count.astype(numpy.uint32))

            # Read remaining data from binary
            fh.write(self.origo.astype(numpy.float64))
            fh.write(self.L.astype(numpy.float64))
            fh.write(self.num.astype(numpy.uint32))
            fh.write(self.periodic.astype(numpy.uint32))

            # Per-particle vectors
            for i in range(self.np):
                fh.write(self.x[i,:].astype(numpy.float64))
                fh.write(self.radius[i].astype(numpy.float64))

            fh.write(self.xysum.astype(numpy.float64))

            for i in range(self.np):
                fh.write(self.vel[i,:].astype(numpy.float64))
                fh.write(self.fixvel[i].astype(numpy.float64))

            fh.write(self.force.astype(numpy.float64))

            fh.write(self.angpos.astype(numpy.float64))
            fh.write(self.angvel.astype(numpy.float64))
            fh.write(self.torque.astype(numpy.float64))

            # Per-particle single-value parameters
            fh.write(self.es_dot.astype(numpy.float64))
            fh.write(self.es.astype(numpy.float64))
            fh.write(self.ev_dot.astype(numpy.float64))
            fh.write(self.ev.astype(numpy.float64))
            fh.write(self.p.astype(numpy.float64))

            fh.write(self.g.astype(numpy.float64))
            fh.write(self.k_n.astype(numpy.float64))
            fh.write(self.k_t.astype(numpy.float64))
            fh.write(self.k_r.astype(numpy.float64))
            fh.write(self.gamma_n.astype(numpy.float64))
            fh.write(self.gamma_t.astype(numpy.float64))
            fh.write(self.gamma_r.astype(numpy.float64))
            fh.write(self.mu_s.astype(numpy.float64))
            fh.write(self.mu_d.astype(numpy.float64))
            fh.write(self.mu_r.astype(numpy.float64))
            fh.write(self.gamma_wn.astype(numpy.float64))
            fh.write(self.gamma_wt.astype(numpy.float64))
            fh.write(self.mu_ws.astype(numpy.float64))
            fh.write(self.mu_wd.astype(numpy.float64))
            fh.write(self.rho.astype(numpy.float64))
            fh.write(self.contactmodel.astype(numpy.uint32))
            fh.write(self.kappa.astype(numpy.float64))
            fh.write(self.db.astype(numpy.float64))
            fh.write(self.V_b.astype(numpy.float64))

            fh.write(self.nw.astype(numpy.uint32))
            for i in range(self.nw):
                fh.write(self.wmode[i].astype(numpy.int32))
            for i in range(self.nw):
                fh.write(self.w_n[i,:].astype(numpy.float64))
                fh.write(self.w_x[i].astype(numpy.float64))

            for i in range(self.nw):
                fh.write(self.w_m[i].astype(numpy.float64))
                fh.write(self.w_vel[i].astype(numpy.float64))
                fh.write(self.w_force[i].astype(numpy.float64))
                fh.write(self.w_devs[i].astype(numpy.float64))
            fh.write(self.w_devs_A.astype(numpy.float64))
            fh.write(self.w_devs_f.astype(numpy.float64))

            fh.write(self.lambda_bar.astype(numpy.float64))
            fh.write(self.nb0.astype(numpy.uint32))
            fh.write(self.sigma_b.astype(numpy.float64))
            fh.write(self.tau_b.astype(numpy.float64))
            for i in range(self.nb0):
                fh.write(self.bonds[i,0].astype(numpy.uint32))
                fh.write(self.bonds[i,1].astype(numpy.uint32))
            fh.write(self.bonds_delta_n.astype(numpy.float64))
            fh.write(self.bonds_delta_t.astype(numpy.float64))
            fh.write(self.bonds_omega_n.astype(numpy.float64))
            fh.write(self.bonds_omega_t.astype(numpy.float64))

            if (self.fluid == True):
                fh.write(self.nu.astype(numpy.float64))
                for z in range(self.num[2]):
                    for y in range(self.num[1]):
                        for x in range(self.num[0]):
                            fh.write(self.v_f[x,y,z,0].astype(numpy.float64))
                            fh.write(self.v_f[x,y,z,1].astype(numpy.float64))
                            fh.write(self.v_f[x,y,z,2].astype(numpy.float64))
                            fh.write(self.p_f[x,y,z].astype(numpy.float64))
                            fh.write(self.phi[x,y,z].astype(numpy.float64))
                            fh.write(self.dphi[x,y,z].astype(numpy.float64))

                fh.write(self.rho_f.astype(numpy.float64))
                fh.write(self.p_mod_A.astype(numpy.float64))
                fh.write(self.p_mod_f.astype(numpy.float64))
                fh.write(self.p_mod_phi.astype(numpy.float64))

                fh.write(self.bc_bot.astype(numpy.int32))
                fh.write(self.bc_top.astype(numpy.int32))
                fh.write(self.free_slip_bot.astype(numpy.int32))
                fh.write(self.free_slip_top.astype(numpy.int32))

        finally:
            if fh is not None:
                fh.close()

    def writeVTKall(self, verbose = True):
        '''
        Writes a VTK file for each simulation output file with particle
        information and the fluid grid to the ``../output/`` folder by default.
        The file name will be in the format ``<self.sid>.vtu`` and
        ``fluid-<self.sid>.vti``. The vtu files can be used to visualize the
        particles, and the vti files for visualizing the fluid in ParaView.

        After opening the vtu files, the particle fields will show up in the
        "Properties" list. Press "Apply" to import all fields into the ParaView
        session. The particles are visualized by selecting the imported data in
        the "Pipeline Browser". Afterwards, click the "Glyph" button in the
        "Common" toolbar, or go to the "Filters" menu, and press "Glyph" from
        the "Common" list. Choose "Sphere" as the "Glyph Type", set "Radius" to
        1.0, choose "scalar" as the "Scale Mode". Check the "Edit" checkbox, and
        set the "Set Scale Factor" to 1.0. The field "Maximum Number of Points"
        may be increased if the number of particles exceed the default value.
        Finally press "Apply", and the particles will appear in the main window. 

        The sphere resolution may be adjusted ("Theta resolution", "Phi
        resolution") to increase the quality and the computational requirements
        of the rendering.

        The fluid grid is visualized by opening the vti files, and pressing
        "Apply" to import all fluid field properties. To visualize the scalar
        fields, such as the pressure, the porosity, the porosity change or the
        velocity magnitude, choose "Surface" or "Surface With Edges" as the
        "Representation". Choose the desired property as the "Coloring" field.
        It may be desirable to show the color bar by pressing the "Show" button,
        and "Rescale" to fit the color range limits to the current file. The
        coordinate system can be displayed by checking the "Show Axis" field.
        All adjustments by default require the "Apply" button to be pressed
        before regenerating the view.

        The fluid vector fields (e.g. the fluid velocity) can be visualizing by
        e.g. arrows. To do this, select the fluid data in the "Pipeline
        Browser". Press "Glyph" from the "Common" toolbar, or go to the
        "Filters" mennu, and press "Glyph" from the "Common" list. Make sure
        that "Arrow" is selected as the "Glyph type", and "Velocity" as the
        "Vectors" value. Adjust the "Maximum Number of Points" to be at least as
        big as the number of fluid cells in the grid. Press "Apply" to visualize
        the arrows.

        If several data files are generated for the same simulation (e.g. using
        the :func:`writeVTKall()` function), it is able to step the visualization
        through time by using the ParaView controls.

        :param verbose: Show diagnostic information (default = True)
        :type verbose: bool
        '''

        lastfile = status(self.sid)
        sb = Spherebin(fluid = self.fluid)
        for i in range(lastfile+1):
            fn = "../output/{0}.output{1:0=5}.bin".format(self.sid, i)
            sb.sid = self.sid + ".{:0=5}".format(i)
            sb.readbin(fn, verbose = False)
            sb.writeVTK()
            if (self.fluid == True):
                sb.writeFluidVTK(verbose=verbose)


    def writeVTK(self, folder = '../output/', verbose = True):
        '''
        Writes a VTK file with particle information to the ``../output/`` folder
        by default. The file name will be in the format ``<self.sid>.vtu``.
        The vtu files can be used to visualize the particles in ParaView.

        After opening the vtu files, the particle fields will show up in the
        "Properties" list. Press "Apply" to import all fields into the ParaView
        session. The particles are visualized by selecting the imported data in
        the "Pipeline Browser". Afterwards, click the "Glyph" button in the
        "Common" toolbar, or go to the "Filters" menu, and press "Glyph" from
        the "Common" list. Choose "Sphere" as the "Glyph Type", set "Radius" to
        1.0, choose "scalar" as the "Scale Mode". Check the "Edit" checkbox, and
        set the "Set Scale Factor" to 1.0. The field "Maximum Number of Points"
        may be increased if the number of particles exceed the default value.
        Finally press "Apply", and the particles will appear in the main window. 

        The sphere resolution may be adjusted ("Theta resolution", "Phi
        resolution") to increase the quality and the computational requirements
        of the rendering. All adjustments by default require the "Apply" button
        to be pressed before regenerating the view.

        If several vtu files are generated for the same simulation (e.g. using
        the :func:``writeVTKall()`` function), it is able to step the
        visualization through time by using the ParaView controls.

        :param folder: The folder where to place the output binary file (default
            (default = '../output/')
        :type folder: str
        :param verbose: Show diagnostic information (default = True)
        :type verbose: bool
        '''

        fh = None
        try :
            targetbin = folder + '/' + self.sid + '.vtu' # unstructured grid
            if (verbose == True):
                print('Output file: {0}'.format(targetbin))

            fh = open(targetbin, 'w')

            # the VTK data file format is documented in
            # http://www.vtk.org/VTK/img/file-formats.pdf

            fh.write('<?xml version="1.0"?>\n') # XML header
            fh.write('<VTKFile type="UnstructuredGrid" version="0.1" '
                    + 'byte_order="LittleEndian">\n') # VTK header
            fh.write('  <UnstructuredGrid>\n')
            fh.write('    <Piece NumberOfPoints="{}" '.format(self.np[0])
                    + 'NumberOfCells="0">\n')

            # Coordinates for each point (positions)
            fh.write('      <Points>\n')
            fh.write('        <DataArray name="Position" type="Float32" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.x[i,0], self.x[i,1], self.x[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')
            fh.write('      </Points>\n')
            
            ### Data attributes
            fh.write('      <PointData Scalars="Radius" Vectors="vector">\n')

            # Radii
            fh.write('        <DataArray type="Float32" Name="Radius" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.radius[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # xysum.x
            fh.write('        <DataArray type="Float32" Name="Xdisplacement" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.xysum[i,0]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # xysum.y
            fh.write('        <DataArray type="Float32" Name="Ydisplacement" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.xysum[i,1]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Velocity
            fh.write('        <DataArray type="Float32" Name="Velocity" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.vel[i,0], self.vel[i,1], self.vel[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # fixvel
            fh.write('        <DataArray type="Float32" Name="FixedVel" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.fixvel[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Force
            fh.write('        <DataArray type="Float32" Name="Force" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.force[i,0], self.force[i,1], self.force[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Angular Position
            fh.write('        <DataArray type="Float32" Name="AngularPosition" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.angpos[i,0], self.angpos[i,1], self.angpos[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Angular Velocity
            fh.write('        <DataArray type="Float32" Name="AngularVelocity" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.angvel[i,0], self.angvel[i,1], self.angvel[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Torque
            fh.write('        <DataArray type="Float32" Name="Torque" '
                    + 'NumberOfComponents="3" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} {} {} '.format(\
                        self.torque[i,0], self.torque[i,1], self.torque[i,2]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Shear energy rate
            fh.write('        <DataArray type="Float32" Name="ShearEnergyRate" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.es_dot[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Shear energy
            fh.write('        <DataArray type="Float32" Name="ShearEnergy" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.es[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Viscous energy rate
            fh.write('        <DataArray type="Float32" '
                    + 'Name="ViscousEnergyRate" format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.ev_dot[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Shear energy
            fh.write('        <DataArray type="Float32" Name="ViscousEnergy" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.ev[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')

            # Pressure
            fh.write('        <DataArray type="Float32" Name="Pressure" '
                    + 'format="ascii">\n')
            fh.write('          ')
            for i in range(self.np):
                fh.write('{} '.format(self.p[i]))
            fh.write('\n')
            fh.write('        </DataArray>\n')


            fh.write('      </PointData>\n')
            fh.write('      <Cells>\n')
            fh.write('        <DataArray type="Int32" Name="connectivity" '
                    + 'format="ascii">\n')
            fh.write('        </DataArray>\n')
            fh.write('        <DataArray type="Int32" Name="offsets" '
                    + 'format="ascii">\n')
            fh.write('        </DataArray>\n')
            fh.write('        <DataArray type="UInt8" Name="types" '
                    + 'format="ascii">\n')
            fh.write('        </DataArray>\n')
            fh.write('      </Cells>\n')
            fh.write('    </Piece>\n')
            fh.write('  </UnstructuredGrid>\n')
            fh.write('</VTKFile>')

        finally:
            if fh is not None:
                fh.close()

    def writeFluidVTK(self, folder = '../output/', verbose = True):
        '''
        Writes a VTK file for the fluid grid to the ``../output/`` folder by
        default. The file name will be in the format ``fluid-<self.sid>.vti``.
        The vti files can be used for visualizing the fluid in ParaView.

        The fluid grid is visualized by opening the vti files, and pressing
        "Apply" to import all fluid field properties. To visualize the scalar
        fields, such as the pressure, the porosity, the porosity change or the
        velocity magnitude, choose "Surface" or "Surface With Edges" as the
        "Representation". Choose the desired property as the "Coloring" field.
        It may be desirable to show the color bar by pressing the "Show" button,
        and "Rescale" to fit the color range limits to the current file. The
        coordinate system can be displayed by checking the "Show Axis" field.
        All adjustments by default require the "Apply" button to be pressed
        before regenerating the view.

        The fluid vector fields (e.g. the fluid velocity) can be visualizing by
        e.g. arrows. To do this, select the fluid data in the "Pipeline
        Browser". Press "Glyph" from the "Common" toolbar, or go to the
        "Filters" mennu, and press "Glyph" from the "Common" list. Make sure
        that "Arrow" is selected as the "Glyph type", and "Velocity" as the
        "Vectors" value. Adjust the "Maximum Number of Points" to be at least as
        big as the number of fluid cells in the grid. Press "Apply" to visualize
        the arrows.

        If several data files are generated for the same simulation (e.g. using
        the :func:`writeVTKall()` function), it is able to step the
        visualization through time by using the ParaView controls.

        :param folder: The folder where to place the output binary file (default
            (default = '../output/')
        :type folder: str
        :param verbose: Show diagnostic information (default = True)
        :type verbose: bool
        '''

        filename = folder + '/fluid-' + self.sid + '.vti' # image grid

        # initalize VTK data structure
        grid = vtk.vtkImageData()
        dx = (self.L-self.origo)/self.num   # cell center spacing
        grid.SetOrigin(self.origo + 0.5*dx)
        grid.SetSpacing(dx)
        grid.SetDimensions(self.num)    # no. of points in each direction

        # array of scalars: hydraulic pressures
        pres = vtk.vtkDoubleArray()
        pres.SetName("Pressure")
        pres.SetNumberOfComponents(1)
        pres.SetNumberOfTuples(grid.GetNumberOfPoints())

        # array of vectors: hydraulic velocities
        vel = vtk.vtkDoubleArray()
        vel.SetName("Velocity")
        vel.SetNumberOfComponents(3)
        vel.SetNumberOfTuples(grid.GetNumberOfPoints())

        # array of scalars: porosities
        poros = vtk.vtkDoubleArray()
        poros.SetName("Porosity")
        poros.SetNumberOfComponents(1)
        poros.SetNumberOfTuples(grid.GetNumberOfPoints())

        # array of scalars: porosity change
        dporos = vtk.vtkDoubleArray()
        dporos.SetName("Porosity change")
        dporos.SetNumberOfComponents(1)
        dporos.SetNumberOfTuples(grid.GetNumberOfPoints())

        # insert values
        for z in range(self.num[2]):
            for y in range(self.num[1]):
                for x in range(self.num[0]):
                    idx = x + self.num[0]*y + self.num[0]*self.num[1]*z;
                    pres.SetValue(idx, self.p_f[x,y,z])
                    vel.SetTuple(idx, self.v_f[x,y,z,:])
                    poros.SetValue(idx, self.phi[x,y,z])
                    dporos.SetValue(idx, self.dphi[x,y,z])

        # add pres array to grid
        grid.GetPointData().AddArray(pres)
        grid.GetPointData().AddArray(vel)
        grid.GetPointData().AddArray(poros)
        grid.GetPointData().AddArray(dporos)

        # write VTK XML image data file
        writer = vtk.vtkXMLImageDataWriter()
        writer.SetFileName(filename)
        writer.SetInput(grid)
        writer.Update()
        if (verbose == True):
            print('Output file: {0}'.format(filename))


    def readfirst(self, verbose=True):
        '''
        Read the first output file from the ``../output/`` folder, corresponding
        to the object simulation id (``self.sid``).

        :param verbose: Display diagnostic information (default = True)
        :type verbose: bool

        See also :func:`readbin()`, :func:`readlast()`, :func:`readsecond`, and
        :func:`readstep`.
        '''

        fn = "../output/{0}.output00000.bin".format(self.sid)
        self.readbin(fn, verbose)

    def readsecond(self, verbose=True):
        '''
        Read the second output file from the ``../output/`` folder,
        corresponding to the object simulation id (``self.sid``).

        :param verbose: Display diagnostic information (default = True)
        :type verbose: bool

        See also :func:`readbin()`, :func:`readfirst()`, :func:`readlast()`,
        and :func:`readstep`.
        '''
        fn = "../output/{0}.output00001.bin".format(self.sid)
        self.readbin(fn, verbose)

    def readstep(self, step, verbose=True):
        '''
        Read a output file from the ``../output/`` folder, corresponding
        to the object simulation id (``self.sid``).

        :param step: The output file number to read, starting from 0.
        :type step: int
        :param verbose: Display diagnostic information (default = True)
        :type verbose: bool

        See also :func:`readbin()`, :func:`readfirst()`, :func:`readlast()`,
        and :func:`readsecond`.
        '''
        fn = "../output/{0}.output{1:0=5}.bin".format(self.sid, step)

    def readlast(self, verbose=True):
        '''
        Read the last output file from the ``../output/`` folder, corresponding
        to the object simulation id (``self.sid``).

        :param verbose: Display diagnostic information (default = True)
        :type verbose: bool

        See also :func:`readbin()`, :func:`readfirst()`, :func:`readsecond`, and
        :func:`readstep`.
        '''
        lastfile = status(self.sid)
        fn = "../output/{0}.output{1:0=5}.bin".format(self.sid, lastfile)
        self.readbin(fn, verbose)

    def generateRadii(self, psd = 'logn',
            radius_mean = 440e-6,
            radius_variance = 8.8e-9,
            histogram = True):
        '''
        Draw random particle radii from a selected probability distribution.
        The larger the variance of radii is, the slower the computations will
        run. The reason is two-fold: The smallest particle dictates the time
        step length, where smaller particles cause shorter time steps. At the
        same time, the largest particle determines the sorting cell size, where
        larger particles cause larger cells. Larger cells are likely to contain
        more particles, causing more contact checks.

        :param psd: The particle side distribution. One possible value is
            ``logn``, which is a log-normal probability distribution, suitable
            for approximating well-sorted, coarse sediments. The other possible
            value is ``uni``, which is a uniform distribution from
            ``radius_mean-radius_variance`` to ``radius_mean+radius_variance``.
        :type psd: str
        :param radius_mean: The mean radius [m] (default = 440e-6 m)
        :type radius_mean: float
        :param radius_variance: The variance in the probability distribution
            [m].
        :type radius_variance: float

        See also: :func:`generateBimodalRadii()`.
        '''

        if psd == 'logn': # Log-normal probability distribution
            mu = math.log(\
                    (radius_mean**2)/math.sqrt(radius_variance+radius_mean**2))
            sigma = math.sqrt(math.log(radius_variance/(radius_mean**2)+1))
            self.radius = numpy.random.lognormal(mu, sigma, self.np)
        if psd == 'uni':  # Uniform distribution
            radius_min = radius_mean - radius_variance
            radius_max = radius_mean + radius_variance
            self.radius = numpy.random.uniform(radius_min, radius_max, self.np)

        # Show radii as histogram
        if (histogram == True):
            fig = plt.figure(figsize=(15,10), dpi=300)
            figtitle = 'Particle size distribution, {0} particles'.format(\
                    self.np[0])
            fig.text(0.5,0.95,figtitle,horizontalalignment='center',\
                    fontproperties=FontProperties(size=18))
            bins = 20

            # Create histogram
            plt.hist(self.radius, bins)

            # Plot
            plt.xlabel('Radii [m]')
            plt.ylabel('Count')
            plt.axis('tight')
            fig.savefig(self.sid + '-psd.png')
            fig.clf()

    def generateBimodalRadii(self,
            r_small = 0.005,
            r_large = 0.05,
            ratio = 0.2,
            verbose = True):
        '''
        Draw random radii from two distinct sizes.

        :param r_small: Radii of small population [m], in ]0;r_large[
        :type r_small: float
        :param r_large: Radii of large population [m], in ]r_small;inf[
        :type r_large: float
        :param ratio: Approximate volumetric ratio between the two
            populations (large/small).
        :type ratio: float

        See also: :func:`generateRadii()`.
        '''
        if (r_small >= r_large):
            raise Exception("r_large should be larger than r_small")

        V_small = V_sphere(r_small)
        V_large = V_sphere(r_large)
        nlarge = int(V_small/V_large * ratio * self.np[0])  # ignore void volume

        self.radius[:] = r_small
        self.radius[0:nlarge] = r_large
        numpy.random.shuffle(self.radius)

        # Test volumetric ratio
        V_small_total = V_small * (self.np - nlarge)
        V_large_total = V_large * nlarge
        if (abs(V_large_total/V_small_total - ratio) > 1.0e5):
            raise Exception("Volumetric ratio seems wrong")

        if (verbose == True):
            print("generateBimodalRadii created " + str(nlarge)
                    + " large particles, and " + str(self.np[0] - nlarge)
                    + " small")


    def initRandomPos(self, g = numpy.array([0.0, 0.0, -9.80665]),
            gridnum = numpy.array([12, 12, 36]),
            periodic = 1,
            contactmodel = 2):
        '''
        Initialize particle positions in loose, cubic configuration. Radii
        *must* be set beforehand. If the x and y boundaries are set as periodic,
        the particle centers will be placed all the way to the edge. On regular,
        non-periodic boundaries, the particles are restrained at the edges to
        make space for their radii within the bounding box.

        :param g: The vector of gravitational acceleration (default = [0, 0,
            -9.90665])
        :type g: numpy.array
        :param gridnum: The number of sorting cells in each spatial direction
            (default = [12, 12, 36])
        :type gridnum: numpy.array
        :param periodic: Set if the x and y boundaries are periodic (no = 0, yes 
            = 1, default = 1)
        :type periodic: int
        :param contactmodel: The type of tangential contact model to use
            (visco-frictional = 1, elasto-visco-frictional = 2, default = 2)
        :type contactmodel: int
        '''
        self.g = g
        self.periodic[0] = periodic

        # Calculate cells in grid
        self.num = gridnum

        # World size
        r_max = numpy.amax(self.radius)
        cellsize = 2 * r_max
        self.L = self.num * cellsize

        # Particle positions randomly distributed without overlap
        for i in range(self.np):
            overlaps = True
            while overlaps == True:
                overlaps = False

                # Draw random position
                for d in range(self.nd):
                    self.x[i,d] = (self.L[d] - self.origo[d] - 2*r_max) \
                            * numpy.random.random_sample() \
                            + self.origo[d] + r_max

                # Check other particles for overlaps
                for j in range(i-1):
                    delta = self.x[i] - self.x[j]
                    delta_len = math.sqrt(numpy.dot(delta,delta)) \
                            - (self.radius[i] + self.radius[j])
                    if (delta_len < 0.0):
                        overlaps = True
            print("\rFinding non-overlapping particle positions, "
                    + "{0} % complete".format(numpy.ceil(i/self.np[0]*100)))

        # Print newline
        print()

        self.contactmodel[0] = contactmodel


    def defineWorldBoundaries(self, L, origo=[0.0, 0.0, 0.0]):
        '''
        Set the boundaries of the world. Particles will only be able to interact
        within this domain. With dynamic walls, allow space for expansions.
        *Important*: The particle radii have to be set beforehand. The world
        edges act as static walls.

        :param L: The upper boundary of the domain [m]
        :type L: numpy.array
        :param origo: The lower boundary of the domain [m]. Negative values
            won't work. Default = [0.0, 0.0, 0.0].
        :type origo: numpy.array
        '''

        # Cell configuration
        cellsize_min = 2.1 * numpy.amax(self.radius)

        # Lower boundary of the sorting grid
        self.origo[:] = origo[:]

        # Upper boundary of the sorting grid
        self.L[:] = L[:]

        # Adjust the number of sorting cells along each axis to fit the largest
        # particle size and the world size
        self.num[0] = numpy.ceil((self.L[0]-self.origo[0])/cellsize_min)
        self.num[1] = numpy.ceil((self.L[1]-self.origo[1])/cellsize_min)
        self.num[2] = numpy.ceil((self.L[2]-self.origo[2])/cellsize_min)

        #if (self.num.any() < 4):
        if (self.num[0] < 4 or self.num[1] < 4 or self.num[2] < 4):
            raise Exception("Error: The grid must be at least 3 cells in each "
            + "direction\nGrid: x={}, y={}, z={}\n".format(\
                    self.num[0], self.num[1], self.num[2])
            + "Please increase the world size.")


    def initGrid(self):
        ''' Initialize grid suitable for the particle positions set previously.
            The margin parameter adjusts the distance (in no. of max. radii)
            from the particle boundaries.
        '''

        # Cell configuration
        cellsize_min = 2.1 * numpy.amax(self.radius)
        self.num[0] = numpy.ceil((self.L[0]-self.origo[0])/cellsize_min)
        self.num[1] = numpy.ceil((self.L[1]-self.origo[1])/cellsize_min)
        self.num[2] = numpy.ceil((self.L[2]-self.origo[2])/cellsize_min)

        if (self.num[0] < 4 or self.num[1] < 4 or self.num[2] < 4):
            raise Exception("Error: The grid must be at least 3 cells in each "
            + "direction\nGrid: x={}, y={}, z={}".format(\
                    self.num[0], self.num[1], self.num[2]))

        # Put upper wall at top boundary
        if (self.nw > 0):
            self.w_x[0] = self.L[0]


    # Generate grid based on particle positions
    def initGridAndWorldsize(self, g = numpy.array([0.0, 0.0, -9.80665]),
            margin = 2.0,
            periodic = 1,
            contactmodel = 2):
        ''' Initialize grid suitable for the particle positions set previously.
            The margin parameter adjusts the distance (in no. of max. radii)
            from the particle boundaries.
        '''

        self.g = g
        self.periodic[0] = periodic

        # Cell configuration
        r_max = numpy.amax(self.radius)

        # Max. and min. coordinates of world
        self.origo = numpy.array([numpy.amin(self.x[:,0] - self.radius[:]),
            numpy.amin(self.x[:,1] - self.radius[:]),
            numpy.amin(self.x[:,2] - self.radius[:])]) \
                    - margin*r_max
        self.L = numpy.array([numpy.amax(self.x[:,0] + self.radius[:]),
            numpy.amax(self.x[:,1] + self.radius[:]),
            numpy.amax(self.x[:,2] + self.radius[:])]) \
                    + margin*r_max

        cellsize_min = 2.1 * r_max
        self.num[0] = numpy.ceil((self.L[0]-self.origo[0])/cellsize_min)
        self.num[1] = numpy.ceil((self.L[1]-self.origo[1])/cellsize_min)
        self.num[2] = numpy.ceil((self.L[2]-self.origo[2])/cellsize_min)

        if (self.num[0] < 4 or self.num[1] < 4 or self.num[2] < 4):
            raise Exception("Error: The grid must be at least 3 cells in each "
            + "direction, num = " + str(self.num))

        self.contactmodel[0] = contactmodel

        # Put upper wall at top boundary
        if (self.nw > 0):
            self.w_x[0] = self.L[0]


    # Initialize particle positions to regular, grid-like, non-overlapping
    # configuration
    def initGridPos(self, g = numpy.array([0.0, 0.0, -9.80665]),
            gridnum = numpy.array([12, 12, 36]),
            periodic = 1,
            contactmodel = 2):
        ''' Initialize particle positions in loose, cubic configuration.
            Radii must be set beforehand.
            xynum is the number of rows in both x- and y- directions.
        '''

        self.g = g
        self.periodic[0] = periodic

        # Calculate cells in grid
        self.num = gridnum

        # World size
        r_max = numpy.amax(self.radius)
        cellsize = 2.1 * r_max
        self.L = self.num * cellsize

        # Check whether there are enough grid cells
        if ((self.num[0]*self.num[1]*self.num[2]-(2**3)) < self.np):
            print("Error! The grid is not sufficiently large.")
            raise NameError('Error! The grid is not sufficiently large.')

        gridpos = numpy.zeros(self.nd, dtype=numpy.uint32)

        # Make sure grid is sufficiently large if every second level is moved
        if (self.periodic[0] == 1):
            self.num[0] -= 1
            self.num[1] -= 1

        # Check whether there are enough grid cells
        if ((self.num[0]*self.num[1]*self.num[2]-(2*3*3)) < self.np):
            print("Error! The grid is not sufficiently large.")
            raise NameError('Error! The grid is not sufficiently large.')


        # Particle positions randomly distributed without overlap
        for i in range(self.np):

            # Find position in 3d mesh from linear index
            gridpos[0] = (i % (self.num[0]))
            gridpos[1] = numpy.floor(i/(self.num[0])) % (self.num[0])
            gridpos[2] = numpy.floor(i/((self.num[0])*(self.num[1]))) #\
                    #% ((self.num[0])*(self.num[1]))

            for d in range(self.nd):
                self.x[i,d] = gridpos[d] * cellsize + 0.5*cellsize

            # Allow pushing every 2.nd level out of lateral boundaries
            if (self.periodic[0] == 1):
                # Offset every second level
                if (gridpos[2] % 2):
                    self.x[i,0] += 0.5*cellsize
                    self.x[i,1] += 0.5*cellsize

        self.contactmodel[0] = contactmodel

        # Readjust grid to correct size
        if (self.periodic[0] == 1):
            self.num[0] += 1
            self.num[1] += 1


    def initRandomGridPos(self, g = numpy.array([0.0, 0.0, -9.80665]),
            gridnum = numpy.array([12, 12, 32]),
            periodic = 1,
            contactmodel = 2):
        ''' Initialize particle positions in loose, cubic configuration.
            Radii must be set beforehand.
            xynum is the number of rows in both x- and y- directions.
        '''

        self.g = g
        self.periodic[0] = periodic

        # Calculate cells in grid
        coarsegrid = numpy.floor(gridnum/2)

        # World size
        r_max = numpy.amax(self.radius)

        # Cells in grid 2*size to make space for random offset
        cellsize = 2.1 * r_max * 2

        # Check whether there are enough grid cells
        if (((coarsegrid[0]-1)*(coarsegrid[1]-1)*(coarsegrid[2]-1)) < self.np):
            print("Error! The grid is not sufficiently large.")
            raise NameError('Error! The grid is not sufficiently large.')

        gridpos = numpy.zeros(self.nd, dtype=numpy.uint32)

        # Particle positions randomly distributed without overlap
        for i in range(self.np):

            # Find position in 3d mesh from linear index
            gridpos[0] = (i % (coarsegrid[0]))
            gridpos[1] = numpy.floor(i/(coarsegrid[0])) % (coarsegrid[0])
            gridpos[2] = numpy.floor(i/((coarsegrid[0])*(coarsegrid[1])))

            # Place particles in grid structure, and randomly adjust the
            # positions within the oversized cells (uniform distribution)
            for d in range(self.nd):
                r = self.radius[i]*1.05
                self.x[i,d] = gridpos[d] * cellsize \
                        + ((cellsize-r) - r) * numpy.random.random_sample() + r

        self.contactmodel[0] = contactmodel

        # Calculate new grid with cell size equal to max. particle diameter
        x_max = numpy.max(self.x[:,0] + self.radius)
        y_max = numpy.max(self.x[:,1] + self.radius)
        z_max = numpy.max(self.x[:,2] + self.radius)
        # Adjust size of world
        self.num[0] = numpy.ceil(x_max/cellsize)
        self.num[1] = numpy.ceil(y_max/cellsize)
        self.num[2] = numpy.ceil(z_max/cellsize)
        self.L = self.num * cellsize

    def createBondPair(self, i, j, spacing=-0.1):
        ''' Bond particles i and j. Particle j is moved adjacent to particle i,
        and oriented randomly.
        @param spacing (float) The inter-particle distance prescribed. Positive
        values result in a inter-particle distance, negative equal an overlap.
        The value is relative to the sum of the two radii.
        '''

        x_i = self.x[i]
        r_i = self.radius[i]
        r_j = self.radius[j]
        dist_ij = (r_i + r_j)*(1.0 + spacing)

        dazi = numpy.random.rand(1) * 360.0  # azimuth
        azi = numpy.radians(dazi)
        dang = numpy.random.rand(1) * 180.0 - 90.0 # angle
        ang = numpy.radians(dang)

        x_j = numpy.copy(x_i)
        x_j[0] = x_j[0] + dist_ij * numpy.cos(azi) * numpy.cos(ang)
        x_j[1] = x_j[1] + dist_ij * numpy.sin(azi) * numpy.cos(ang)
        x_j[2] = x_j[2] + dist_ij * numpy.sin(ang) * numpy.cos(azi)
        self.x[j] = x_j

        if (self.x[j,0] < self.origo[0]):
            self.x[j,0] += x_i[0] - x_j[0]
        if (self.x[j,1] < self.origo[1]):
            self.x[j,1] += x_i[1] - x_j[1]
        if (self.x[j,2] < self.origo[2]):
            self.x[j,2] += x_i[2] - x_j[2]

        if (self.x[j,0] > self.L[0]):
            self.x[j,0] -= abs(x_j[0] - x_i[0])
        if (self.x[j,1] > self.L[1]):
            self.x[j,1] -= abs(x_j[1] - x_i[1])
        if (self.x[j,2] > self.L[2]):
            self.x[j,2] -= abs(x_j[2] - x_i[2])

        self.bond(i,j)     # register bond

        # Check that the spacing is correct
        x_ij = self.x[i] - self.x[j]
        x_ij_length = numpy.sqrt(x_ij.dot(x_ij))
        if ((x_ij_length - dist_ij) > dist_ij*0.01):
            print(x_i); print(r_i)
            print(x_j); print(r_j)
            print(x_ij_length); print(dist_ij)
            raise Exception("Error, something went wrong in createBondPair")


    def random2bonds(self, ratio=0.3, spacing=-0.1):
        ''' Bond an amount of particles in two-particle clusters @param ratio:
        The amount of particles to bond, values in ]0.0;1.0] (float)
        @param spacing: The distance relative to the sum of radii between bonded
        particles, neg. values denote an overlap. Values in ]0.0,inf[ (float).
        The particles should be initialized beforehand.
        Note: The actual number of bonds is likely to be somewhat smaller than
        specified, due to the random selection algorithm.
        '''

        bondparticles = numpy.unique(\
                numpy.random.random_integers(0, high=self.np-1,\
                size=int(self.np*ratio)))
        if (bondparticles.size % 2 > 0):
            bondparticles = bondparticles[:-1].copy()
        bondparticles =\
                bondparticles.reshape(int(bondparticles.size/2), 2).copy()

        for n in numpy.arange(bondparticles.shape[0]):
            self.createBondPair(bondparticles[n,0], bondparticles[n,1], spacing)

    def zeroKinematics(self):
        'Zero kinematics of particles'

        self.vel = numpy.zeros(self.np*self.nd, dtype=numpy.float64)\
                .reshape(self.np, self.nd)
        self.angvel = numpy.zeros(self.np*self.nd, dtype=numpy.float64)\
                .reshape(self.np, self.nd)
        self.angpos = numpy.zeros(self.np*self.nd, dtype=numpy.float64)\
                .reshape(self.np, self.nd)
        self.es = numpy.zeros(self.np, dtype=numpy.float64)
        self.ev = numpy.zeros(self.np, dtype=numpy.float64)
        self.xysum = numpy.zeros(self.np*2, dtype=numpy.float64)\
                .reshape(self.np, 2)

    def adjustUpperWall(self, z_adjust = 1.1):
        'Included for legacy purposes, calls adjustWall with idx=0'

        # Initialize upper wall
        self.nw = numpy.ones(1)
        self.wmode = numpy.zeros(1) # fixed BC
        self.w_n = numpy.zeros(self.nw*self.nd, dtype=numpy.float64).reshape(\
                self.nw,self.nd)
        self.w_n[0,2] = -1.0
        self.w_vel = numpy.zeros(1)
        self.w_force = numpy.zeros(1)
        self.w_devs = numpy.zeros(1)

        self.w_x = numpy.zeros(1)
        self.w_m = numpy.zeros(1)
        self.adjustWall(idx=0, adjust = z_adjust)

    def adjustWall(self, idx, adjust = 1.1):
        'Adjust grid and dynamic wall to max. particle position'

        if (idx == 0):
            dim = 2
        elif (idx == 1 or idx == 2):
            dim = 0
        elif (idx == 3 or idx == 4):
            dim = 1
        else:
            print("adjustWall: idx value not understood")

        xmin = numpy.min(self.x[:,dim] - self.radius)
        xmax = numpy.max(self.x[:,dim] + self.radius)

        cellsize = self.L[0] / self.num[0]

        self.num[dim] = numpy.ceil(((xmax-xmin)*adjust + xmin)/cellsize)
        self.L[dim] = (xmax-xmin)*adjust + xmin

        # Initialize upper wall
        if (idx == 0 or idx == 1 or idx == 3):
            self.w_x[idx] = numpy.array([xmax])
        else:
            self.w_x[idx] = numpy.array([xmin])
        self.w_m[idx] = numpy.array([self.rho[0]*self.np*math.pi \
                *(cellsize/2.0)**3])


    def consolidate(self, deviatoric_stress = 10e3,
            periodic = 1):
        ''' Setup consolidation experiment. Specify the upper wall
            deviatoric stress in Pascal, default value is 10 kPa.
        '''

        # Zero the kinematics of all particles
        self.zeroKinematics()

        # Adjust grid and placement of upper wall
        self.adjustUpperWall()

        # Set the top wall BC to a value of deviatoric stress
        self.wmode = numpy.array([1])
        self.w_devs = numpy.ones(1) * deviatoric_stress

    def uniaxialStrainRate(self, wvel = -0.001,
            periodic = 1):
        ''' Setup consolidation experiment. Specify the upper wall
            velocity in m/s, default value is -0.001 m/s (i.e. downwards).
        '''

        # zero kinematics
        self.zeroKinematics()

        # Initialize upper wall
        self.adjustUpperWall()
        self.wmode = numpy.array([2]) # strain rate BC
        self.w_vel = numpy.array([wvel])

    def triaxial(self, wvel = -0.001, deviatoric_stress = 10.0e3):
        ''' Setup triaxial experiment. The upper wall is moved at a fixed
            velocity in m/s, default values is -0.001 m/s (i.e. downwards).
            The side walls are exerting a deviatoric stress
        '''

        # zero kinematics
        self.zeroKinematics()

        # Initialize walls
        self.nw[0] = 5  # five dynamic walls
        self.wmode  = numpy.array([2,1,1,1,1]) # BCs (vel, stress, stress, ...)
        self.w_vel  = numpy.array([1,0,0,0,0]) * wvel
        self.w_devs = numpy.array([0,1,1,1,1]) * deviatoric_stress
        self.w_n = numpy.array(([0,0,-1], [-1,0,0], [1,0,0], [0,-1,0], [0,1,0]),
                dtype=numpy.float64)
        self.w_x = numpy.zeros(5)
        self.w_m = numpy.zeros(5)
        self.w_force = numpy.zeros(5)
        for i in range(5):
            self.adjustWall(idx=i)


    def shear(self,
            shear_strain_rate = 1,
            periodic = 1):
        ''' Setup shear experiment. Specify the upper wall
            deviatoric stress in Pascal, default value is 10 kPa.
            The shear strain rate is the shear length divided by the
            initial height per second.
        '''

        # Find lowest and heighest point
        z_min = numpy.min(self.x[:,2] - self.radius)
        z_max = numpy.max(self.x[:,2] + self.radius)

        # the grid cell size is equal to the max. particle diameter
        cellsize = self.L[0] / self.num[0]

        # make grid one cell heigher to allow dilation
        self.num[2] += 1
        self.L[2] = self.num[2] * cellsize

        # zero kinematics
        self.zeroKinematics()

        # set the thickness of the horizons of fixed particles
        #fixheight = 2*cellsize
        #fixheight = cellsize

        # Fix horizontal velocity to 0.0 of lowermost particles
        d_max_below = numpy.max(self.radius[numpy.nonzero(self.x[:,2] <
            (z_max-z_min)*0.3)])*2.0
        #I = numpy.nonzero(self.x[:,2] < (z_min + fixheight))
        I = numpy.nonzero(self.x[:,2] < (z_min + d_max_below))
        self.fixvel[I] = 1
        self.angvel[I,0] = 0.0
        self.angvel[I,1] = 0.0
        self.angvel[I,2] = 0.0
        self.vel[I,0] = 0.0 # x-dim
        self.vel[I,1] = 0.0 # y-dim

        # Fix horizontal velocity to specific value of uppermost particles
        d_max_top = numpy.max(self.radius[numpy.nonzero(self.x[:,2] >
            (z_max-z_min)*0.7)])*2.0
        #I = numpy.nonzero(self.x[:,2] > (z_max - fixheight))
        I = numpy.nonzero(self.x[:,2] > (z_max - d_max_top))
        self.fixvel[I] = 1
        self.angvel[I,0] = 0.0
        self.angvel[I,1] = 0.0
        self.angvel[I,2] = 0.0
        self.vel[I,0] = (z_max-z_min)*shear_strain_rate
        self.vel[I,1] = 0.0 # y-dim


        # Set wall viscosities to zero
        self.gamma_wn[0] = 0.0
        self.gamma_wt[0] = 0.0

        # Set wall friction coefficients to zero
        self.mu_ws[0] = 0.0
        self.mu_wd[0] = 0.0

    def initTemporal(self, total,
            current = 0.0,
            file_dt = 0.05,
            step_count = 0):
        ''' Set temporal parameters for the simulation.
            Particle radii, physical parameters, and the optional fluid grid
            need to be set prior to these.
        '''

        r_min = numpy.amin(self.radius)

        # Computational time step (O'Sullivan et al, 2003)
        #self.time_dt[0] = 0.17 * \
                #math.sqrt((4.0/3.0 * math.pi * r_min**3 * self.rho[0]) \
                #/ numpy.amax([self.k_n[:], self.k_t[:]]) )
        # Computational time step (Zhang and Campbell, 1992)
        self.time_dt[0] = 0.075 * math.sqrt((V_sphere(r_min) * self.rho[0]) \
                / numpy.amax([self.k_n[:], self.k_t[:]]) )

        # Check numerical stability of the fluid phase, by criteria derived by
        # von Neumann stability analysis of the diffusion and advection terms
        if (self.fluid == True):

            # Cell spacing
            dx = numpy.amin((\
                    self.L[0]/self.num[0],\
                    self.L[1]/self.num[1],\
                    self.L[2]/self.num[2]))

            # Diffusion term
            if (self.nu[0]*self.time_dt[0]/(dx*dx) > 0.5):
                raise Exception("Error: The time step is too large to ensure "
                        + "stability in the diffusive term of the fluid "
                        + "momentum equation.")

            # Normalized velocities
            v_norm = numpy.empty(self.num[0]*self.num[1]*self.num[2])
            idx = 0
            for x in numpy.arange(self.num[0]):
                for y in numpy.arange(self.num[1]):
                    for z in numpy.arange(self.num[2]):
                        v_norm[idx] = numpy.sqrt(self.v_f[x,y,z,:].dot(\
                                self.v_f[x,y,z,:]))
                        idx = idx + 1

            # Advection term. This term has to be reevaluated during the
            # computations, as the fluid velocity changes.
            if (numpy.amax(v_norm)*self.time_dt[0]/dx > 1.0):
                raise Exception("Error: The time step is too large to ensure "
                        + "stability in the advective term of the fluid "
                        + "momentum equation.")

        # Time at start
        self.time_current[0] = current
        self.time_total[0] = total
        self.time_file_dt[0] = file_dt
        self.time_step_count[0] = 0

    def initFluid(self, nu = 8.9e-4):
        ''' Initialize the fluid arrays and the fluid viscosity '''
        self.nu[0] = nu
        self.p_f = numpy.ones((self.num[0], self.num[1], self.num[2]),
                dtype=numpy.float64)
        self.v_f = numpy.zeros((self.num[0], self.num[1], self.num[2], self.nd),
                dtype=numpy.float64)
        self.phi = numpy.ones((self.num[0], self.num[1], self.num[2]),
                dtype=numpy.float64)
        self.dphi = numpy.zeros((self.num[0], self.num[1], self.num[2]),
                dtype=numpy.float64)

    def defaultParams(self,
            mu_s = 0.4,
            mu_d = 0.4,
            mu_r = 0.0,
            rho = 2600,
            k_n = 1.16e9,
            k_t = 1.16e9,
            k_r = 0,
            gamma_n = 0,
            gamma_t = 0,
            gamma_r = 0,
            gamma_wn = 1e4,
            gamma_wt = 1e4,
            capillaryCohesion = 0):
        ''' Initialize particle parameters to default values.
            Radii must be set prior to calling this function.
        '''

        # Particle material density, kg/m^3
        self.rho = numpy.ones(1, dtype=numpy.float64) * rho


        ### Dry granular material parameters

        # Contact normal elastic stiffness, N/m
        self.k_n = numpy.ones(1, dtype=numpy.float64) * k_n

        # Contact shear elastic stiffness (for contactmodel = 2), N/m
        self.k_t = numpy.ones(1, dtype=numpy.float64) * k_t

        # Contact rolling elastic stiffness (for contactmodel = 2), N/m
        self.k_r = numpy.ones(1, dtype=numpy.float64) * k_r

        # Contact normal viscosity. Critical damping: 2*sqrt(m*k_n).
        # Normal force component elastic if nu = 0.0.
        #self.gamma_n = numpy.ones(self.np, dtype=numpy.float64) \
                #          * nu_frac * 2.0 * math.sqrt(4.0/3.0 * math.pi \
                #          * numpy.amin(self.radius)**3 \
                #          * self.rho[0] * self.k_n[0])
        self.gamma_n = numpy.ones(1, dtype=numpy.float64) * gamma_n

        # Contact shear viscosity, Ns/m
        self.gamma_t = numpy.ones(1, dtype=numpy.float64) * gamma_t

        # Contact rolling viscosity, Ns/m?
        self.gamma_r = numpy.ones(1, dtype=numpy.float64) * gamma_r

        # Contact static shear friction coefficient
        #self.mu_s = numpy.ones(1, dtype=numpy.float64) * \
                #numpy.tan(numpy.radians(ang_s))
        self.mu_s = numpy.ones(1, dtype=numpy.float64) * mu_s

        # Contact dynamic shear friction coefficient
        #self.mu_d = numpy.ones(1, dtype=numpy.float64) * \
                #numpy.tan(numpy.radians(ang_d))
        self.mu_d = numpy.ones(1, dtype=numpy.float64) * mu_d

        # Contact rolling friction coefficient
        #self.mu_r = numpy.ones(1, dtype=numpy.float64) * \
                #numpy.tan(numpy.radians(ang_r))
        self.mu_r = numpy.ones(1, dtype=numpy.float64) * mu_r

        # Wall viscosities
        self.gamma_wn[0] = gamma_wn # normal
        self.gamma_wt[0] = gamma_wt # sliding

        # Wall friction coefficients
        self.mu_ws = self.mu_s  # static
        self.mu_wd = self.mu_d  # dynamic

        ### Parameters related to capillary bonds

        # Wettability, 0=perfect
        theta = 0.0;
        if (capillaryCohesion == 1):
            # Prefactor
            self.kappa[0] = 2.0 * math.pi * gamma_t * numpy.cos(theta)
            self.V_b[0] = 1e-12  # Liquid volume at bond
        else :
            self.kappa[0] = 0.0;  # Zero capillary force
            self.V_b[0] = 0.0;    # Zero liquid volume at bond

        # Debonding distance
        self.db[0] = (1.0 + theta/2.0) * self.V_b**(1.0/3.0)


    def bond(self, i, j):
        ''' Create a bond between particles i and j '''

        self.lambda_bar[0] = 1.0 # Radius multiplier to parallel-bond radii

        if (hasattr(self, 'bonds') == False):
            self.bonds = numpy.array([[i,j]], dtype=numpy.uint32)
        else :
            self.bonds = numpy.vstack((self.bonds, [i,j]))

        if (hasattr(self, 'bonds_delta_n') == False):
            self.bonds_delta_n = numpy.array([0.0], dtype=numpy.uint32)
        else :
            #self.bonds_delta_n = numpy.vstack((self.bonds_delta_n, [0.0]))
            self.bonds_delta_n = numpy.append(self.bonds_delta_n, [0.0])

        if (hasattr(self, 'bonds_delta_t') == False):
            self.bonds_delta_t = numpy.array([[0.0, 0.0, 0.0]],\
                    dtype=numpy.uint32)
        else :
            self.bonds_delta_t = numpy.vstack((self.bonds_delta_t,\
                    [0.0, 0.0, 0.0]))

        if (hasattr(self, 'bonds_omega_n') == False):
            self.bonds_omega_n = numpy.array([0.0], dtype=numpy.uint32)
        else :
            #self.bonds_omega_n = numpy.vstack((self.bonds_omega_n, [0.0]))
            self.bonds_omega_n = numpy.append(self.bonds_omega_n, [0.0])

        if (hasattr(self, 'bonds_omega_t') == False):
            self.bonds_omega_t = numpy.array([[0.0, 0.0, 0.0]],\
                    dtype=numpy.uint32)
        else :
            self.bonds_omega_t = numpy.vstack((self.bonds_omega_t,\
                    [0.0, 0.0, 0.0]))

        # Increment the number of bonds with one
        self.nb0 += 1

    def currentDevs(self):
        ''' Return current magnitude of the deviatoric normal stress '''
        return w_devs[0] + w_devs_A*numpy.sin(2.0*numpy.pi*self.time_current)

    def energy(self, method):
        ''' Calculate the sum of the energy components of all particles.
        '''

        if method == 'pot':
            m = numpy.ones(self.np)*4.0/3.0*math.pi*self.radius**3*self.rho
            return numpy.sum(m*math.sqrt(numpy.dot(self.g,self.g))*self.x[:,2])

        elif method == 'kin':
            m = numpy.ones(self.np)*4.0/3.0*math.pi*self.radius**3*self.rho
            esum = 0.0
            for i in range(self.np):
                esum += 0.5*m[i]*math.sqrt(\
                        numpy.dot(self.vel[i,:],self.vel[i,:]))**2
            return esum

        elif method == 'rot':
            m = numpy.ones(self.np)*4.0/3.0*math.pi*self.radius**3*self.rho
            esum = 0.0
            for i in range(self.np):
                esum += 0.5*2.0/5.0*m[i]*self.radius[i]**2 \
                        *math.sqrt(\
                        numpy.dot(self.angvel[i,:],self.angvel[i,:]))**2
            return esum

        elif method == 'shear':
            return numpy.sum(self.es)

        elif method == 'shearrate':
            return numpy.sum(self.es_dot)

        elif method == 'visc_n':
            return numpy.sum(self.ev)

        elif method == 'visc_n_rate':
            return numpy.sum(self.ev_dot)

        elif method == 'bondpot':
            if (self.nb0 > 0):
                R_bar = self.lambda_bar*numpy.minimum(\
                        self.radius[self.bonds[:,0]],\
                        self.radius[self.bonds[:,1]])
                A = numpy.pi*R_bar**2
                I = 0.25*numpy.pi*R_bar**4
                J = I*2.0
                bondpot_fn = numpy.sum(\
                        0.5*A*self.k_n*numpy.abs(self.bonds_delta_n)**2)
                bondpot_ft = numpy.sum(\
                        0.5*A*self.k_t*numpy.linalg.norm(self.bonds_delta_t)**2)
                bondpot_tn = numpy.sum(\
                        0.5*J*self.k_t*numpy.abs(self.bonds_omega_n)**2)
                bondpot_tt = numpy.sum(\
                        0.5*I*self.k_n*numpy.linalg.norm(self.bonds_omega_t)**2)
                return bondpot_fn + bondpot_ft + bondpot_tn + bondpot_tt
            else :
                return 0.0

    def voidRatio(self):
        'Returns the current void ratio'

        # Find the bulk volume
        V_t = (self.L[0] - self.origo[0]) \
                *(self.L[1] - self.origo[1]) \
                *(self.w_x[0] - self.origo[2])

        # Find the volume of solids
        V_s = numpy.sum(4.0/3.0 * math.pi * self.radius**3)

        # Return the void ratio
        e = (V_t - V_s)/V_s
        return e

    def bulkPorosity(self):
        ''' Calculate and return the bulk porosity '''

        if (self.nw == 0):
            V_total = self.L[0] * self.L[1] * self.L[2]
        elif (self.nw == 1):
            V_total = self.L[0] * self.L[1] * self.w_x[0]
            if (V_total <= 0.0):
                raise Exception("Could not determine total volume")

        # Find the volume of solids
        V_solid = numpy.sum(V_sphere(self.radius))
        return (V_total - V_solid) / V_total

    def porosity(self,
            slices = 10,
            verbose = False):
        ''' Calculate the porosity as a function of depth, by averaging values
            in horizontal slabs.
            Returns porosity values and depth
        '''

        # Write data as binary
        self.writebin(verbose=False)

        # Run porosity program on binary
        pipe = subprocess.Popen(\
                ["../porosity",\
                "-s","{}".format(slices),\
                "../input/" + self.sid + ".bin"],\
                stdout=subprocess.PIPE)
        output, err = pipe.communicate()

        if (err):
            print(err)
            raise Exception("Could not run external 'porosity' program")

        # read one line of output at a time
        s2 = output.split('\n')
        depth = []
        porosity = []
        for row in s2:
            if (row != '\n' or row != '' or row != ' '): # skip blank lines
                s3 = row.split('\t')
                if (s3 != '' and len(s3) == 2): # make sure line has two vals
                    depth.append(float(s3[0]))
                    porosity.append(float(s3[1]))

        return numpy.array(porosity), numpy.array(depth)

    def run(self, verbose=True, hideinputfile=False, dry=False, valgrind=False,
            cudamemcheck=False):
        'Execute ``sphere`` with target project'

        quiet = ""
        stdout = ""
        dryarg = ""
        valgrindbin = ""
        cudamemchk = ""
        binary = "sphere"
        if (verbose == False):
            quiet = "-q "
        if (hideinputfile == True):
            stdout = " > /dev/null"
        if (dry == True):
            dryarg = "--dry "
        if (valgrind == True):
            valgrindbin = "valgrind -q "
        if (cudamemcheck == True):
            cudamemchk = "cuda-memcheck --leak-check full "
        if (self.fluid == True):
            binary = "porousflow"

        cmd = "cd ..; " + valgrindbin + cudamemchk + "./" + binary + " " \
                + quiet + dryarg + "input/" + self.sid + ".bin " + stdout
        #print(cmd)
        status = subprocess.call(cmd, shell=True)

        if (status != 0):
            print("Warning: the sphere run returned with status " + str(status))

    def torqueScript(self,
            email="adc@geo.au.dk",
            email_alerts="ae",
            walltime="24:00:00",
            queue="qfermi",
            cudapath="/com/cuda/4.0.17/cuda",
            spheredir="/home/adc/code/sphere",
            workdir="/scratch"):
        'Create job script for the Torque queue manager for the binary'

        filename = self.sid + ".sh"
        fh = None
        try :
            fh = open(filename, "w")

            fh.write('#!/bin/sh\n')
            fh.write('#PBS -N ' + self.sid + '\n')
            fh.write('#PBS -l nodes=1:ppn=1\n')
            fh.write('#PBS -l walltime=' + walltime + '\n')
            fh.write('#PBS -q ' + queue + '\n')
            fh.write('#PBS -M ' + email + '\n')
            fh.write('#PBS -m ' + email_alerts + '\n')
            fh.write('CUDAPATH=' + cudapath + '\n')
            fh.write('export PATH=$CUDAPATH/bin:$PATH\n')
            fh.write('export LD_LIBRARY_PATH=$CUDAPATH/lib64'
                    + ':$CUDAPATH/lib:$LD_LIBRARY_PATH\n')
            fh.write('echo "`whoami`@`hostname`"\n')
            fh.write('echo "Start at `date`"\n')
            fh.write('ORIGDIR=' + spheredir + '\n')
            fh.write('WORKDIR=' + workdir + "/$PBS_JOBID\n")
            fh.write('cp -r $ORIGDIR/* $WORKDIR\n')
            fh.write('cd $WORKDIR\n')
            fh.write('cmake . && make\n')
            fh.write('./sphere input/' + self.sid + '.bin > /dev/null &\n')
            fh.write('wait\n')
            fh.write('cp $WORKDIR/output/* $ORIGDIR/output/\n')
            fh.write('echo "End at `date`"\n')

        finally :
            if fh is not None:
                fh.close()

    def render(self,
            method = "pres",
            max_val = 1e3,
            lower_cutoff = 0.0,
            graphicsformat = "png",
            verbose=True):
        ''' Render all output files that belong to the simulation, determined by
        sid.'''

        print("Rendering {} images with the raytracer".format(self.sid))

        quiet = ""
        if (verbose == False):
            quiet = "-q"

        # Render images using sphere raytracer
        if (method == "normal"):
            subprocess.call("cd ..; for F in `ls output/" + self.sid
                    + "*.bin`; do ./sphere " + quiet
                    + " --render $F; done", shell=True)
        else :
            subprocess.call("cd ..; for F in `ls output/" + self.sid
                    + "*.bin`; do ./sphere " + quiet
                    + " --method " + method + " {}".format(max_val)
                    + " -l {}".format(lower_cutoff)
                    + " --render $F; done", shell=True)

        # Convert images to compressed format
        convert()

    def video(self,
        out_folder = "./",
        video_format = "mp4",
        graphics_folder = "../img_out/",
        graphics_format = "png",
        fps = 25,
        qscale = 1,
        bitrate = 1800,
        verbose = False):
        ''' Use ffmpeg to combine images to animation. All images should be
        rendered beforehand.'''

        video(self.sid, out_folder, video_format, graphics_folder, \
              graphics_format, fps, qscale, bitrate, verbose)

    def shearvel(self):
        ''' Calculates and returns the shear velocity (gamma_dot) of the
        experiment'''

        # Find the fixed particles
        fixvel = numpy.nonzero(self.fixvel > 0.0)

        # The shear velocity is the x-axis velocity value of the upper particles
        return self.vel[fixvel,0].max()

    def shearstrain(self):
        ''' Calculates and returns the current shear strain (gamma) value of the
        experiment. '''

        # Current height
        w_x0 = self.w_x[0]

        # Displacement of the upper, fixed particles in the shear direction
        xdisp = self.time_current[0] * self.shearvel()

        # Return shear strain
        return xdisp/w_x0

    def forcechains(self, lc=200.0, uc=650.0, outformat='png', disp='2d'):
        ''' Visualizes the force chains in the system from the magnitude of the
        normal contact forces, and produces an image of them.
        @param lc: Lower cutoff of contact forces. Contacts below are not
        visualized (float)
        @param uc: Upper cutoff of contact forces. Contacts above are
        visualized with this value (float)
        @param outformat: Format of output image. Possible values are
        'interactive', 'png', 'epslatex', 'epslatex-color'
        @param disp: Display forcechains in '2d' or '3d'
        Warning: Will segfault if no contacts are found.
        '''

        self.writebin()

        nd = ''
        if (disp == '2d'):
            nd = '-2d '

        subprocess.call("cd .. && ./forcechains " + nd + "-f " + outformat \
                + " -lc " + str(lc) + " -uc " + str(uc) + " input/" + self.sid \
                + ".bin > python/tmp.gp", shell=True)
        subprocess.call("gnuplot tmp.gp && rm tmp.bin && rm tmp.gp", shell=True)


    def forcechainsRose(self, lower_limit=0.25):
        ''' Visualize strike- and dip angles of the strongest force chains in a
        rose plot.
        '''
        self.writebin(verbose=False)

        subprocess.call("cd .. && ./forcechains -f txt input/" + self.sid \
                + ".bin > python/fc-tmp.txt", shell=True)

        # data will have the shape (numcontacts, 7)
        data = numpy.loadtxt("fc-tmp.txt", skiprows=1)

        # find the max. value of the normal force
        f_n_max = numpy.amax(data[:,6])

        # specify the lower limit of force chains to do statistics on
        f_n_lim = lower_limit * f_n_max * 0.6

        # find the indexes of these contacts
        I = numpy.nonzero(data[:,6] > f_n_lim)

        # loop through these contacts and find the strike and dip of the
        # contacts
        strikelist = [] # strike direction of the normal vector, [0:360[
        diplist = [] # dip of the normal vector, [0:90]
        for i in I[0]:

            x1 = data[i,0]
            y1 = data[i,1]
            z1 = data[i,2]
            x2 = data[i,3]
            y2 = data[i,4]
            z2 = data[i,5]

            if (z1 < z2):
                xlower = x1; ylower = y1; zlower = z1
                xupper = x2; yupper = y2; zupper = z2
            else :
                xlower = x2; ylower = y2; zlower = z2
                xupper = x1; yupper = y1; zupper = z1

            # Vector pointing downwards
            dx = xlower - xupper
            dy = ylower - yupper
            dz = zlower - zupper
            dhoriz = numpy.sqrt(dx**2 + dy**2)

            # Find dip angle
            diplist.append(math.degrees(math.atan((zupper - zlower)/dhoriz)))

            # Find strike angle
            if (ylower >= yupper): # in first two quadrants
                strikelist.append(math.acos(dx/dhoriz))
            else :
                strikelist.append(2.0*numpy.pi - math.acos(dx/dhoriz))


        plt.figure(figsize=[4,4])
        ax = plt.subplot(111, polar=True, axisbg="w")
        ax.scatter(strikelist, diplist, c='k', marker='+')
        ax.set_rmax(90)
        ax.set_rticks([])
        plt.savefig("fc-" + self.sid + "-rose.pdf", transparent=True)

        subprocess.call("rm fc-tmp.txt", shell=True)

    def bondsRose(self, imgformat = "pdf"):
        ''' Visualize strike- and dip angles of the bond pairs in a rose plot.
        '''
        # loop through these contacts and find the strike and dip of the
        # contacts
        strikelist = [] # strike direction of the normal vector, [0:360[
        diplist = [] # dip of the normal vector, [0:90]
        for n in numpy.arange(self.nb0):

            i = self.bonds[n,0]
            j = self.bonds[n,1]

            x1 = self.x[i,0]
            y1 = self.x[i,1]
            z1 = self.x[i,2]
            x2 = self.x[j,0]
            y2 = self.x[j,1]
            z2 = self.x[j,2]

            if (z1 < z2):
                xlower = x1; ylower = y1; zlower = z1
                xupper = x2; yupper = y2; zupper = z2
            else :
                xlower = x2; ylower = y2; zlower = z2
                xupper = x1; yupper = y1; zupper = z1

            # Vector pointing downwards
            dx = xlower - xupper
            dy = ylower - yupper
            dz = zlower - zupper
            dhoriz = numpy.sqrt(dx**2 + dy**2)

            # Find dip angle
            diplist.append(math.degrees(math.atan((zupper - zlower)/dhoriz)))

            # Find strike angle
            if (ylower >= yupper): # in first two quadrants
                strikelist.append(math.acos(dx/dhoriz))
            else :
                strikelist.append(2.0*numpy.pi - math.acos(dx/dhoriz))


        plt.figure(figsize=[4,4])
        ax = plt.subplot(111, polar=True, axisbg="w")
        ax.scatter(strikelist, diplist, c='k', marker='+')
        ax.set_rmax(90)
        ax.set_rticks([])
        plt.savefig("bonds-" + self.sid + "-rose." + imgformat,\
                transparent=True)

    def status(self):
        '''
        Returns the current simulation status by using the simulation id
        (``sid``) as an identifier.
        
        :returns: The number of the last output file written
        :return type: int
        '''
        return status(self.sid)


    def totalMomentum(self):
        '''
        Returns the sum of particle momentums.

        :returns: The sum of particle momentums (m*v) [N*s]
        :return type: float
        '''
        v_norm = vector_norm(self.vel)
        return numpy.sum(V_sphere(self.radius))*self.rho*v_norm

    def sheardisp(self, outformat='pdf', zslices=32):
        ''' Show particle x-displacement vs. the z-pos '''

        # Bin data and error bars for alternative visualization
        h_total = numpy.max(self.x[:,2]) - numpy.min(self.x[:,2])
        h_slice = h_total / zslices

        zpos = numpy.zeros(zslices)
        xdisp = numpy.zeros(zslices)
        err = numpy.zeros(zslices)

        for iz in range(zslices):

            # Find upper and lower boundaries of bin
            zlower = iz * h_slice
            zupper = zlower + h_slice

            # Save depth
            zpos[iz] = zlower + 0.5*h_slice

            # Find particle indexes within that slice
            I = numpy.nonzero((self.x[:,2] > zlower) & (self.x[:,2] < zupper))

            # Save mean x displacement
            xdisp[iz] = numpy.mean(self.xysum[I,0])

            # Save x displacement standard deviation
            err[iz] = numpy.std(self.xysum[I,0])

        plt.figure(figsize=[4, 4])
        ax = plt.subplot(111)
        ax.scatter(self.xysum[:,0], self.x[:,2], c='gray', marker='+')
        ax.errorbar(xdisp, zpos, xerr=err,
                    c='black', linestyle='-', linewidth=1.4)
        ax.set_xlabel("Horizontal particle displacement, [m]")
        ax.set_ylabel("Vertical position, [m]")
        plt.savefig(self.sid + '-sheardisp.' + outformat, transparent=True)

    def porosities(self, outformat='pdf', zslices=16):
        ''' Plot porosities with depth '''

        porosity, depth = self.porosity(zslices)

        plt.figure(figsize=[4, 4])
        ax = plt.subplot(111)
        ax.plot(porosity, depth,
                c='black', linestyle='-', linewidth=1.4)
        ax.set_xlabel("Horizontally averaged porosity, [-]")
        ax.set_ylabel("Vertical position, [m]")
        plt.savefig(self.sid + '-porositiy.' + outformat, transparent=True)



    def thinsection_x1x3(self,
            x2 = 'center',
            graphicsformat = 'png',
            cbmax = None,
            arrowscale = 0.01,
            velarrowscale = 1.0,
            slipscale = 1.0,
            verbose = False):
        ''' Produce a 2D image of particles on a x1,x3 plane, intersecting the
            second axis at x2.
            Output is saved as '<sid>-ts-x1x3.txt' in the current folder.

            An upper limit to the pressure color bar range can be set by the
            cbmax parameter.

            The data can be plotted in gnuplot with:
                gnuplot> set size ratio -1
                gnuplot> set palette defined (0 "blue", 0.5 "gray", 1 "red")
                gnuplot> plot '<sid>-ts-x1x3.txt' with circles palette fs \
                        transparent solid 0.4 noborder
        '''

        if (x2 == 'center') :
            x2 = (self.L[1] - self.origo[1]) / 2.0

        # Initialize plot circle positionsr, radii and pressures
        ilist = []
        xlist = []
        ylist = []
        rlist = []
        plist = []
        pmax = 0.0
        rmax = 0.0
        axlist = []
        aylist = []
        daxlist = []
        daylist = []
        dvxlist = []
        dvylist = []
        # Black circle at periphery of particles with angvel[:,1] > 0.0
        cxlist = []
        cylist = []
        crlist = []

        # Loop over all particles, find intersections
        for i in range(self.np):

            delta = abs(self.x[i,1] - x2)   # distance between centre and plane

            if (delta < self.radius[i]): # if the sphere intersects the plane

                # Store particle index
                ilist.append(i)

                # Store position on plane
                xlist.append(self.x[i,0])
                ylist.append(self.x[i,2])

                # Store radius of intersection
                r_circ = math.sqrt(self.radius[i]**2 - delta**2)
                if (r_circ > rmax):
                    rmax = r_circ
                rlist.append(r_circ)

                # Store pos. and radius if it is spinning around pos. y
                if (self.angvel[i,1] > 0.0):
                    cxlist.append(self.x[i,0])
                    cylist.append(self.x[i,2])
                    crlist.append(r_circ)

                # Store pressure
                pval = self.p[i]
                if (cbmax != None):
                    if (pval > cbmax):
                        pval = cbmax
                plist.append(pval)

                # Store rotational velocity data for arrows
                # Save two arrows per particle
                axlist.append(self.x[i,0]) # x starting point of arrow
                axlist.append(self.x[i,0]) # x starting point of arrow

                # y starting point of arrow
                aylist.append(self.x[i,2] + r_circ*0.5)

                # y starting point of arrow
                aylist.append(self.x[i,2] - r_circ*0.5)

                # delta x for arrow end point
                daxlist.append(self.angvel[i,1]*arrowscale)

                # delta x for arrow end point
                daxlist.append(-self.angvel[i,1]*arrowscale)
                daylist.append(0.0) # delta y for arrow end point
                daylist.append(0.0) # delta y for arrow end point

                # Store linear velocity data

                # delta x for arrow end point
                dvxlist.append(self.vel[i,0]*velarrowscale)

                # delta y for arrow end point
                dvylist.append(self.vel[i,2]*velarrowscale)

                if (r_circ > self.radius[i]):
                    raise Exception("Error, circle radius is larger than the "
                    + "particle radius")
                if (self.p[i] > pmax):
                    pmax = self.p[i]

        if (verbose == True):
            print("Max. pressure of intersecting spheres: " + str(pmax) + " Pa")
            if (cbmax != None):
                print("Value limited to: " + str(cbmax) + " Pa")

        # Save circle data
        filename = '../gnuplot/data/' + self.sid + '-ts-x1x3.txt'
        fh = None
        try :
            fh = open(filename, 'w')

            for (x, y, r, p) in zip(xlist, ylist, rlist, plist):
                fh.write("{}\t{}\t{}\t{}\n".format(x, y, r, p))

        finally :
            if fh is not None:
                fh.close()

        # Save circle data for articles spinning with pos. y
        filename = '../gnuplot/data/' + self.sid + '-ts-x1x3-circ.txt'
        fh = None
        try :
            fh = open(filename, 'w')

            for (x, y, r) in zip(cxlist, cylist, crlist):
                fh.write("{}\t{}\t{}\n".format(x, y, r))

        finally :
            if fh is not None:
                fh.close()

        # Save angular velocity data. The arrow lengths are normalized to max.
        # radius
        #   Output format: x, y, deltax, deltay
        #   gnuplot> plot '-' using 1:2:3:4 with vectors head filled lt 2
        filename = '../gnuplot/data/' + self.sid + '-ts-x1x3-arrows.txt'
        fh = None
        try :
            fh = open(filename, 'w')

            for (ax, ay, dax, day) in zip(axlist, aylist, daxlist, daylist):
                fh.write("{}\t{}\t{}\t{}\n".format(ax, ay, dax, day))

        finally :
            if fh is not None:
                fh.close()

        # Save linear velocity data
        #   Output format: x, y, deltax, deltay
        #   gnuplot> plot '-' using 1:2:3:4 with vectors head filled lt 2
        filename = '../gnuplot/data/' + self.sid + '-ts-x1x3-velarrows.txt'
        fh = None
        try :
            fh = open(filename, 'w')

            for (x, y, dvx, dvy) in zip(xlist, ylist, dvxlist, dvylist):
                fh.write("{}\t{}\t{}\t{}\n".format(x, y, dvx, dvy))

        finally :
            if fh is not None:
                fh.close()



        # Check whether there are slips between the particles intersecting the
        # plane
        sxlist = []
        sylist = []
        dsxlist = []
        dsylist = []
        anglelist = [] # angle of the slip vector
        slipvellist = [] # velocity of the slip
        for i in ilist:

            # Loop through other particles, and check whether they are in
            # contact
            for j in ilist:
                #if (i < j):
                if (i != j):

                    # positions
                    x_i = self.x[i,:]
                    x_j = self.x[j,:]

                    # radii
                    r_i = self.radius[i]
                    r_j = self.radius[j]

                    # Inter-particle vector
                    x_ij = x_i - x_j
                    x_ij_length = numpy.sqrt(x_ij.dot(x_ij))

                    # Check for overlap
                    if (x_ij_length - (r_i + r_j) < 0.0):

                        # contact plane normal vector
                        n_ij = x_ij / x_ij_length

                        vel_i = self.vel[i,:]
                        vel_j = self.vel[j,:]
                        angvel_i = self.angvel[i,:]
                        angvel_j = self.angvel[j,:]

                        # Determine the tangential contact surface velocity in
                        # the x,z plane
                        dot_delta = (vel_i - vel_j) \
                                + r_i * numpy.cross(n_ij, angvel_i) \
                                + r_j * numpy.cross(n_ij, angvel_j)

                        # Subtract normal component to get tangential velocity
                        dot_delta_n = n_ij * numpy.dot(dot_delta, n_ij)
                        dot_delta_t = dot_delta - dot_delta_n

                        # Save slip velocity data for gnuplot
                        if (dot_delta_t[0] != 0.0 or dot_delta_t[2] != 0.0):

                            # Center position of the contact
                            cpos = x_i - x_ij * 0.5

                            sxlist.append(cpos[0])
                            sylist.append(cpos[2])
                            dsxlist.append(dot_delta_t[0] * slipscale)
                            dsylist.append(dot_delta_t[2] * slipscale)
                            #anglelist.append(math.degrees(\
                                    #math.atan(dot_delta_t[2]/dot_delta_t[0])))
                            anglelist.append(\
                                    math.atan(dot_delta_t[2]/dot_delta_t[0]))
                            slipvellist.append(\
                                    numpy.sqrt(dot_delta_t.dot(dot_delta_t)))


        # Write slip lines to text file
        filename = '../gnuplot/data/' + self.sid + '-ts-x1x3-slips.txt'
        fh = None
        try :
            fh = open(filename, 'w')

            for (sx, sy, dsx, dsy) in zip(sxlist, sylist, dsxlist, dsylist):
                fh.write("{}\t{}\t{}\t{}\n".format(sx, sy, dsx, dsy))

        finally :
            if fh is not None:
                fh.close()

        # Plot thinsection with gnuplot script
        gamma = self.shearstrain()
        subprocess.call('''cd ../gnuplot/scripts && gnuplot -e "sid='{}'; ''' \
                + '''gamma='{:.4}'; xmin='{}'; xmax='{}'; ymin='{}'; ''' \
                + '''ymax='{}'" plotts.gp'''.format(\
                self.sid, self.shearstrain(), self.origo[0], self.L[0], \
                self.origo[2], self.L[2]), shell=True)

        # Find all particles who have a slip velocity higher than slipvel
        slipvellimit = 0.01
        slipvels = numpy.nonzero(numpy.array(slipvellist) > slipvellimit)


        # Bin slip angle data for histogram
        binno = 36/2
        hist_ang, bins_ang = numpy.histogram(numpy.array(anglelist)[slipvels],\
                bins=binno, density=False)
        center_ang = (bins_ang[:-1] + bins_ang[1:]) / 2.0

        center_ang_mirr = numpy.concatenate((center_ang, center_ang + math.pi))
        hist_ang_mirr = numpy.tile(hist_ang, 2)

        # Write slip angles to text file
        #numpy.savetxt(self.sid + '-ts-x1x3-slipangles.txt', zip(center_ang,\
                #hist_ang), fmt="%f\t%f")

        fig = plt.figure()
        ax = fig.add_subplot(111, polar=True)
        ax.bar(center_ang_mirr, hist_ang_mirr, width=30.0/180.0)
        fig.savefig('../img_out/' + self.sid + '-ts-x1x3-slipangles.png')
        fig.clf()

    def plotFluidDensitiesY(self, y = -1, imgformat = 'png'):

        if (y == -1):
            y = self.num[1]/2

        plt.figure(figsize=[8,8])
        plt.title("Fluid densities")
        imgplt = plt.imshow(self.f_rho[:,y,:].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.xlabel('$x_1$')
        plt.ylabel('$x_3$')
        plt.colorbar()
        plt.savefig('f_rho-' + self.sid + \
                '-y' + str(y) + '.' + imgformat, transparent=False)

    def plotFluidDensitiesZ(self, z = -1, imgformat = 'png'):

        if (z == -1):
            z = self.num[2]/2

        plt.figure(figsize=[8,8])
        plt.title("Fluid densities")
        imgplt = plt.imshow(self.f_rho[:,:,z].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.xlabel('$x_1$')
        plt.ylabel('$x_2$')
        plt.colorbar()
        plt.savefig('f_rho-' + self.sid + \
                '-z' + str(z) + '.' + imgformat, transparent=False)

    def plotFluidVelocitiesY(self, y = -1, imgformat = 'png'):

        if (y == -1):
            y = self.num[1]/2

        plt.title("Fluid velocities")
        plt.figure(figsize=[8,8])

        plt.subplot(131)
        imgplt = plt.imshow(self.f_v[:,y,:,0].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_1$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_3$')
        plt.colorbar(orientation = 'horizontal')

        plt.subplot(132)
        imgplt = plt.imshow(self.f_v[:,y,:,1].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_2$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_3$')
        plt.colorbar(orientation = 'horizontal')

        plt.subplot(133)
        imgplt = plt.imshow(self.f_v[:,y,:,2].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_3$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_3$')
        plt.colorbar(orientation = 'horizontal')

        plt.savefig('f_v-' + self.sid + \
                '-y' + str(y) + '.' + imgformat, transparent=False)

    def plotFluidVelocitiesZ(self, z = -1, imgformat = 'png'):

        if (z == -1):
            z = self.num[2]/2

        plt.title("Fluid velocities")
        plt.figure(figsize=[8,8])

        plt.subplot(131)
        imgplt = plt.imshow(self.f_v[:,:,z,0].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_1$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_2$')
        plt.colorbar(orientation = 'horizontal')

        plt.subplot(132)
        imgplt = plt.imshow(self.f_v[:,:,z,1].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_2$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_2$')
        plt.colorbar(orientation = 'horizontal')

        plt.subplot(133)
        imgplt = plt.imshow(self.f_v[:,:,z,2].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.title("$v_3$")
        plt.xlabel('$x_1$')
        plt.ylabel('$x_2$')
        plt.colorbar(orientation = 'horizontal')

        plt.savefig('f_v-' + self.sid + \
                '-z' + str(z) + '.' + imgformat, transparent=False)

    def plotFluidPorositiesY(self, iteration = -1, y = -1, outformat='png'):
        ''' Plot the porosity values from the simulation. If iteration is -1
        (default value), the last output file will be shown. If the y value is
        -1, the center x,z plane will be rendered '''

        phi = numpy.loadtxt('../output/{}.d_phi.output{:0=5}.bin'.format(\
                self.sid, iteration))

        if (y == -1):
            y = self.num[2]/2

        plt.figure(figsize=[8,8])
        imgplt = plt.imshow(phi[:,y,:].T, origin='lower')
        imgplt.set_interpolation('nearest')
        #imgplt.set_interpolation('bicubic')
        #imgplt.set_cmap('hot')
        plt.xlabel('$i_x$')
        plt.ylabel('$i_z$')
        plt.colorbar()
        plt.savefig(self.sid + '-porosities.output{1:0=5}'.format(iteration)\
                + '-y' + str(y) + '.' + imgformat, transparent=False)

    def plotFluidDiffAdvPresZ(self):
        ''' Compare contributions to the velocity from diffusion and advection
        at top boundary, assuming the flow is 1D along the z-axis, phi = 1, and
        dphi = 0. This solution is analog to the predicted velocity and not
        constrained by the conservation of mass. '''

        # The v_z values are read from self.v_f[0,0,:,2]
        dz = self.L[2]/self.num[2]
        rho = 1000.0 # fluid density

        # Central difference gradients
        dvz_dz = (self.v_f[0,0,1:,2] - self.v_f[0,0,:-1,2])/(2.0*dz)
        dvzvz_dz = (self.v_f[0,0,1:,2]**2 - self.v_f[0,0,:-1,2]**2)/(2.0*dz)

        # Diffusive contribution to velocity change
        dvz_diff = 2.0*self.nu/rho*dvz_dz*self.time_dt

        # Advective contribution to velocity change
        dvz_adv = dvzvz_dz*self.time_dt

        # Pressure gradient
        dp_dz = (self.p_f[0,0,1:] - self.p_f[0,0,:-1])/(2.0*dz)

        cellno = numpy.arange(1, self.num[2])

        fig = plt.figure()
        titlesize=12

        plt.subplot(1,3,1)
        plt.title('Pressure', fontsize=titlesize)
        plt.ylabel('$i_z$')
        plt.xlabel('$p_z$')
        plt.plot(self.p_f[0,0,:], numpy.arange(self.num[2]))
        plt.grid()

        plt.subplot(1,3,2)
        plt.title('Pressure gradient', fontsize=titlesize)
        plt.ylabel('$i_z$')
        plt.xlabel('$\Delta p_z$')
        plt.plot(dp_dz, cellno)
        plt.grid()

        plt.subplot(1,3,3)
        plt.title('Velocity prediction terms', fontsize=titlesize)
        plt.ylabel('$i_z$')
        plt.xlabel('$\Delta v_z$')
        plt.plot(dvz_diff, cellno, label='Diffusion')
        plt.plot(dvz_adv, cellno, label='Advection')
        plt.plot(dvz_diff+dvz_adv, cellno, '--', label='Sum')
        leg = plt.legend(loc='best', prop={'size':8})
        leg.get_frame().set_alpha(0.5)
        plt.grid()

        plt.tight_layout()
        plt.savefig('../output/{}-diff_adv-t={:.2e}s-nu={:.2e}Pa-s.png'.format(\
                self.sid, self.time_current[0], self.nu[0]))
        plt.clf()
        plt.close(fig)

    def plotConvergence(self, format='png'):
        '''
        Plot the convergence evolution in the CFD solver. The plot is saved 
        in the output folder with the file name <simulation ID>-conv.<format>.

        :param format: The plot file type (default = 'png')
        :type format: str
        '''
        fig = plt.figure()
        conv = numpy.loadtxt('../output/' + self.sid + '-conv.log')

        plt.title('Convergence evolution in CFD solver in "' + self.sid + '"')
        plt.xlabel('Time step')
        plt.ylabel('Jacobi iterations')
        plt.plot(conv[:,0], conv[:,1])
        plt.grid()
        plt.savefig('../output/' + self.sid + '-conv.' + format)
        plt.clf()
        plt.close(fig)

    def setFluidPressureModulation(self, A, f, phi=0.0):
        '''
        Set the parameters for the sine wave modulating the fluid pressures
        at the top boundary. Note that a cos-wave is obtained with phi=pi/2.

        :param A: Fluctuation amplitude [Pa]
        :type A: float
        :param f: Fluctuation frequency [Hz]
        :type f: float
        :param phi: Fluctuation phase shift (default=0.0)
        :type phi: float

        See also: :func:`disableFluidPressureModulation()`
        '''
        self.p_mod_A[0] = A
        self.p_mod_f[0] = f
        self.p_mod_phi[0] = phi

    def disableFluidPressureModulation(self):
        '''
        Set the parameters for the sine wave modulating the fluid pressures
        at the top boundary to zero.

        See also: :func:`setFluidPressureModulation()`
        '''
        self.setFluidPressureModulation(A = 0.0, f = 0.0)

    def plotPrescribedFluidPressures(self, format='png'):
        ''' Plot the prescribed fluid pressures through time that may be
        modulated through the class parameters p_mod_A, p_mod_f, and p_mod_phi.
        '''

        fig = plt.figure()
        conv = numpy.loadtxt('../output/' + self.sid + '-conv.log')

        plt.title('Prescribed fluid pressures at the top in "' + self.sid + '"')
        plt.xlabel('Time [s]')
        plt.ylabel('Pressure [Pa]')
        t = numpy.linspace(0,self.time_total,\
                self.time_total/self.time_file_dt)
        p = self.p_f[0,0,-1] + \
                self.p_mod_A * \
                numpy.sin(2.0*numpy.pi*self.p_mod_f*t + self.p_mod_phi)
        plt.plot(t, p, '.-')
        plt.grid()
        plt.savefig('../output/' + self.sid + '-pres.' + format)
        plt.clf()
        plt.close(fig)



def convert(graphicsformat = "png",
        folder = "../img_out"):
    'Converts all PPM images in img_out to graphicsformat, using ImageMagick'

    #quiet = " > /dev/null"
    quiet = ""
    # Convert images
    subprocess.call("for F in " + folder \
            + "/*.ppm ; do BASE=`basename $F .ppm`; convert $F " \
            + folder + "/$BASE." + graphicsformat + " " \
            + quiet + " ; done", shell=True)

    # Remove PPM files
    subprocess.call("rm " + folder + "/*.ppm", shell=True)


def render(binary,
        method = "pres",
        max_val = 1e3,
        lower_cutoff = 0.0,
        graphicsformat = "png",
        verbose=True):
    'Render target binary using the ``sphere`` raytracer.'

    quiet = ""
    if (verbose == False):
        quiet = "-q"

    # Render images using sphere raytracer
    if (method == "normal"):
        subprocess.call("cd .. ; ./sphere " + quiet + \
                " --render " + binary, shell=True)
    else :
        subprocess.call("cd .. ; ./sphere " + quiet + \
                " --method " + method + " {}".format(max_val) + \
                " -l {}".format(lower_cutoff) + \
                " --render " + binary, shell=True)

    # Convert images to compressed format
    convert()


def video(project,
        out_folder = "./",
        video_format = "mp4",
        graphics_folder = "../img_out/",
        graphics_format = "png",
        fps = 25,
        qscale = 1,
        bitrate = 1800,
        verbose = False):
    'Use ffmpeg to combine images to animation. All images should be rendered \
    beforehand.'

    # Possible loglevels:
    # quiet, panic, fatal, error, warning, info, verbose, debug
    loglevel = "info" # verbose = True
    if (verbose == False):
        loglevel = "error"

    subprocess.call(\
            "ffmpeg -qscale {0} -r {1} -b {2} -y ".format(\
            qscale, fps, bitrate) \
            + "-loglevel " + loglevel + " " \
            + "-i " + graphics_folder + project + ".output%05d." \
            + graphics_format + " " \
            + out_folder + "/" + project + "." + video_format, shell=True)

def thinsectionVideo(project,
        out_folder = "./",
        video_format = "mp4",
        fps = 25,
        qscale = 1,
        bitrate = 1800,
        verbose = False):
    ''' Use ffmpeg to combine thin section images to animation.
        This function will start off by rendering the images.
    '''

    # Render thin section images (png)
    lastfile = status(project)
    sb = Spherebin(fluid = self.fluid)
    for i in range(lastfile+1):
        fn = "../output/{0}.output{1:0=5}.bin".format(project, i)
        sb.sid = project + ".output{:0=5}".format(i)
        sb.readbin(fn, verbose = False)
        sb.thinsection_x1x3(cbmax = sb.w_devs[0]*4.0)

    # Combine images to animation
    # Possible loglevels:
    # quiet, panic, fatal, error, warning, info, verbose, debug
    loglevel = "info" # verbose = True
    if (verbose == False):
        loglevel = "error"

    subprocess.call(\
            "ffmpeg -qscale {0} -r {1} -b {2} -y ".format(\
            qscale, fps, bitrate) \
            + "-loglevel " + loglevel + " " \
            + "-i ../img_out/" + project + ".output%05d-ts-x1x3.png " \
            + "-vf 'crop=((in_w/2)*2):((in_h/2)*2)' " \
            + out_folder + "/" + project + "-ts-x1x3." + video_format, \
            shell=True)

def visualize(project, method = 'energy', savefig = True, outformat = 'png'):
    ''' Visualize output from the target project,
        where the temporal progress is of interest.
    '''

    lastfile = status(project)

    ### Plotting
    if (outformat != 'txt'):
        fig = plt.figure(figsize=(15,10),dpi=300)

    if method == 'energy':

        # Allocate arrays
        Epot = numpy.zeros(lastfile+1)
        Ekin = numpy.zeros(lastfile+1)
        Erot = numpy.zeros(lastfile+1)
        Es  = numpy.zeros(lastfile+1)
        Ev  = numpy.zeros(lastfile+1)
        Es_dot = numpy.zeros(lastfile+1)
        Ev_dot = numpy.zeros(lastfile+1)
        Ebondpot = numpy.zeros(lastfile+1)
        Esum = numpy.zeros(lastfile+1)

        # Read energy values from project binaries
        sb = Spherebin(fluid = self.fluid)
        for i in range(lastfile+1):
            fn = "../output/{0}.output{1:0=5}.bin".format(project, i)
            sb.readbin(fn, verbose = False)

            Epot[i] = sb.energy("pot")
            Ekin[i] = sb.energy("kin")
            Erot[i] = sb.energy("rot")
            Es[i]   = sb.energy("shear")
            Ev[i]   = sb.energy("visc_n")
            Es_dot[i] = sb.energy("shearrate")
            Ev_dot[i] = sb.energy("visc_n_rate")
            Ebondpot[i] = sb.energy("bondpot")
            Esum[i] = Epot[i] + Ekin[i] + Erot[i] + Es[i] + Ev[i] + Ebondpot[i]

            t = numpy.linspace(0.0, sb.time_current, lastfile+1)

        if (outformat != 'txt'):
            # Potential energy
            ax1 = plt.subplot2grid((2,5),(0,0))
            ax1.set_xlabel('Time [s]')
            ax1.set_ylabel('Total potential energy [J]')
            ax1.plot(t, Epot, '+-')
            ax1.grid()

            # Kinetic energy
            ax2 = plt.subplot2grid((2,5),(0,1))
            ax2.set_xlabel('Time [s]')
            ax2.set_ylabel('Total kinetic energy [J]')
            ax2.plot(t, Ekin, '+-')
            ax2.grid()

            # Rotational energy
            ax3 = plt.subplot2grid((2,5),(0,2))
            ax3.set_xlabel('Time [s]')
            ax3.set_ylabel('Total rotational energy [J]')
            ax3.plot(t, Erot, '+-')
            ax3.grid()

            # Bond energy
            ax4 = plt.subplot2grid((2,5),(0,3))
            ax4.set_xlabel('Time [s]')
            ax4.set_ylabel('Bond energy [J]')
            ax4.plot(t, Ebondpot, '+-')
            ax4.grid()

            # Total energy
            ax5 = plt.subplot2grid((2,5),(0,4))
            ax5.set_xlabel('Time [s]')
            ax5.set_ylabel('Total energy [J]')
            ax5.plot(t, Esum, '+-')
            ax5.grid()

            # Shear energy rate
            ax6 = plt.subplot2grid((2,5),(1,0))
            ax6.set_xlabel('Time [s]')
            ax6.set_ylabel('Frictional dissipation rate [W]')
            ax6.plot(t, Es_dot, '+-')
            ax6.grid()

            # Shear energy
            ax7 = plt.subplot2grid((2,5),(1,1))
            ax7.set_xlabel('Time [s]')
            ax7.set_ylabel('Total frictional dissipation [J]')
            ax7.plot(t, Es, '+-')
            ax7.grid()

            # Visc_n energy rate
            ax8 = plt.subplot2grid((2,5),(1,2))
            ax8.set_xlabel('Time [s]')
            ax8.set_ylabel('Viscous dissipation rate [W]')
            ax8.plot(t, Ev_dot, '+-')
            ax8.grid()

            # Visc_n energy
            ax9 = plt.subplot2grid((2,5),(1,3))
            ax9.set_xlabel('Time [s]')
            ax9.set_ylabel('Total viscous dissipation [J]')
            ax9.plot(t, Ev, '+-')
            ax9.grid()


            # Combined view
            ax10 = plt.subplot2grid((2,5),(1,4))
            ax10.set_xlabel('Time [s]')
            ax10.set_ylabel('Energy [J]')
            ax10.plot(t, Epot, '+-g')
            ax10.plot(t, Ekin, '+-b')
            ax10.plot(t, Erot, '+-r')
            ax10.legend(('$\sum E_{pot}$','$\sum E_{kin}$','$\sum E_{rot}$'),\
                    'upper right', shadow=True)
            ax10.grid()

            fig.tight_layout()

    elif method == 'walls':

        # Read energy values from project binaries
        sb = Spherebin(fluid = self.fluid)
        for i in range(lastfile+1):
            fn = "../output/{0}.output{1:0=5}.bin".format(project, i)
            sb.readbin(fn, verbose = False)

            # Allocate arrays on first run
            if (i == 0):
                wforce = numpy.zeros((lastfile+1)*sb.nw[0],\
                        dtype=numpy.float64).reshape((lastfile+1), sb.nw[0])
                wvel   = numpy.zeros((lastfile+1)*sb.nw[0],\
                        dtype=numpy.float64).reshape((lastfile+1), sb.nw[0])
                wpos   = numpy.zeros((lastfile+1)*sb.nw[0],\
                        dtype=numpy.float64).reshape((lastfile+1), sb.nw[0])
                wdevs  = numpy.zeros((lastfile+1)*sb.nw[0],\
                        dtype=numpy.float64).reshape((lastfile+1), sb.nw[0])
                maxpos = numpy.zeros((lastfile+1), dtype=numpy.float64)
                logstress = numpy.zeros((lastfile+1), dtype=numpy.float64)
                voidratio = numpy.zeros((lastfile+1), dtype=numpy.float64)

            wforce[i] = sb.w_force[0]
            wvel[i]   = sb.w_vel[0]
            wpos[i]   = sb.w_x[0]
            wdevs[i]  = sb.w_devs[0]
            maxpos[i] = numpy.max(sb.x[:,2]+sb.radius)
            logstress[i] = numpy.log((sb.w_force[0]/(sb.L[0]*sb.L[1]))/1000.0)
            voidratio[i] = sb.voidRatio()


        t = numpy.linspace(0.0, sb.time_current, lastfile+1)

        # Plotting
        if (outformat != 'txt'):
            # linear plot of time vs. wall position
            ax1 = plt.subplot2grid((2,2),(0,0))
            ax1.set_xlabel('Time [s]')
            ax1.set_ylabel('Position [m]')
            ax1.plot(t, wpos, '+-', label="upper wall")
            ax1.plot(t, maxpos, '+-', label="heighest particle")
            ax1.legend()
            ax1.grid()

            #ax2 = plt.subplot2grid((2,2),(1,0))
            #ax2.set_xlabel('Time [s]')
            #ax2.set_ylabel('Force [N]')
            #ax2.plot(t, wforce, '+-')

            # semilog plot of log stress vs. void ratio
            ax2 = plt.subplot2grid((2,2),(1,0))
            ax2.set_xlabel('log deviatoric stress [kPa]')
            ax2.set_ylabel('Void ratio [-]')
            ax2.plot(logstress, voidratio, '+-')
            ax2.grid()

            # linear plot of time vs. wall velocity
            ax3 = plt.subplot2grid((2,2),(0,1))
            ax3.set_xlabel('Time [s]')
            ax3.set_ylabel('Velocity [m/s]')
            ax3.plot(t, wvel, '+-')
            ax3.grid()

            # linear plot of time vs. deviatoric stress
            ax4 = plt.subplot2grid((2,2),(1,1))
            ax4.set_xlabel('Time [s]')
            ax4.set_ylabel('Deviatoric stress [Pa]')
            ax4.plot(t, wdevs, '+-', label="$\sigma_0$")
            ax4.plot(t, wforce/(sb.L[0]*sb.L[1]), '+-', label="$\sigma'$")
            ax4.legend(loc=4)
            ax4.grid()

    elif method == 'triaxial':

        # Read energy values from project binaries
        sb = Spherebin(fluid = self.fluid)
        for i in range(lastfile+1):
            fn = "../output/{0}.output{1:0=5}.bin".format(project, i)
            sb.readbin(fn, verbose = False)

            vol = (sb.w_x[0]-sb.origo[2]) * (sb.w_x[1]-sb.w_x[2]) \
                    * (sb.w_x[3] - sb.w_x[4])

            # Allocate arrays on first run
            if (i == 0):
                axial_strain = numpy.zeros(lastfile+1, dtype=numpy.float64)
                deviatoric_stress = numpy.zeros(lastfile+1, dtype=numpy.float64)
                volumetric_strain = numpy.zeros(lastfile+1, dtype=numpy.float64)

                w0pos0 = sb.w_x[0]
                vol0 = vol

            sigma1 = sb.w_force[0]/((sb.w_x[1]-sb.w_x[2])*(sb.w_x[3]-sb.w_x[4]))

            axial_strain[i] = (w0pos0 - sb.w_x[0])/w0pos0
            volumetric_strain[i] = (vol0-vol)/vol0
            deviatoric_stress[i] = sigma1 / sb.w_devs[1]

        #print(lastfile)
        #print(axial_strain)
        #print(deviatoric_stress)
        #print(volumetric_strain)

        # Plotting
        if (outformat != 'txt'):

            # linear plot of deviatoric stress
            ax1 = plt.subplot2grid((2,1),(0,0))
            ax1.set_xlabel('Axial strain, $\gamma_1$, [-]')
            ax1.set_ylabel('Deviatoric stress, $\sigma_1 - \sigma_3$, [Pa]')
            ax1.plot(axial_strain, deviatoric_stress, '+-')
            #ax1.legend()
            ax1.grid()

            #ax2 = plt.subplot2grid((2,2),(1,0))
            #ax2.set_xlabel('Time [s]')
            #ax2.set_ylabel('Force [N]')
            #ax2.plot(t, wforce, '+-')

            # semilog plot of log stress vs. void ratio
            ax2 = plt.subplot2grid((2,1),(1,0))
            ax2.set_xlabel('Axial strain, $\gamma_1$ [-]')
            ax2.set_ylabel('Volumetric strain, $\gamma_v$, [-]')
            ax2.plot(axial_strain, volumetric_strain, '+-')
            ax2.grid()


    elif method == 'shear':

        sb = Spherebin(fluid = self.fluid)
        # Read stress values from project binaries
        for i in range(lastfile+1):
            fn = "../output/{0}.output{1:0=5}.bin".format(project, i)
            sb.readbin(fn, verbose = False)

            # First iteration: Allocate arrays and find constant values
            if (i == 0):
                # Shear displacement
                xdisp     = numpy.zeros(lastfile+1, dtype=numpy.float64)

                # Normal stress
                sigma_eff = numpy.zeros(lastfile+1, dtype=numpy.float64)

                # Normal stress
                sigma_def = numpy.zeros(lastfile+1, dtype=numpy.float64)

                # Shear stress
                tau       = numpy.zeros(lastfile+1, dtype=numpy.float64)

                # Upper wall position
                dilation  = numpy.zeros(lastfile+1, dtype=numpy.float64)

                # Upper wall position
                tau_u = 0.0             # Peak shear stress
                tau_u_shearstrain = 0.0 # Shear strain value of peak sh. stress

                fixvel = numpy.nonzero(sb.fixvel > 0.0)
                #fixvel_upper = numpy.nonzero(sb.vel[fixvel,0] > 0.0)
                shearvel = sb.vel[fixvel,0].max()
                w_x0 = sb.w_x[0]        # Original height
                A = sb.L[0] * sb.L[1]   # Upper surface area

            # Summation of shear stress contributions
            for j in fixvel[0]:
                if (sb.vel[j,0] > 0.0):
                    tau[i] += -sb.force[j,0]

            if (i > 0):
                xdisp[i]    = xdisp[i-1] + sb.time_file_dt[0] * shearvel
            sigma_eff[i] = sb.w_force[0] / A
            sigma_def[i] = sb.w_devs[0]
            dilation[i] = sb.w_x[0] - w_x0                # dilation in meters
            #dilation[i] = (sb.w_x[0] - w_x0)/w_x0 * 100.0 # dilation in percent

            # Test if this was the max. shear stress
            if (tau[i] > tau_u):
                tau_u = tau[i]
                tau_u_shearstrain = xdisp[i]/w_x0


        # Plot stresses
        if (outformat != 'txt'):
            shearinfo = "$\\tau_u$ = {:.3} Pa at $\gamma$ = {:.3}".format(\
                    tau_u, tau_u_shearstrain)
            fig.text(0.5, 0.03, shearinfo, horizontalalignment='center',
                     fontproperties=FontProperties(size=14))
            ax1 = plt.subplot2grid((1, 2), (0, 0))
            ax1.set_xlabel('Shear strain [-]')
            ax1.set_ylabel('Stress [Pa]')
            ax1.plot(xdisp / w_x0, sigma_eff, '+-g', label="$\sigma'$")
            ax1.plot(xdisp / w_x0, sigma_def, '+-b', label="$\sigma_0$")
            ax1.plot(xdisp / w_x0, tau, '+-r', label="$\\tau$")
            ax1.legend(loc=4)
            ax1.grid()

            # Plot dilation
            ax2 = plt.subplot2grid((1,2),(0,1))
            ax2.set_xlabel('Shear strain [-]')
            ax2.set_ylabel('Dilation [m]')
            ax2.plot(xdisp/w_x0, dilation, '+-')
            ax2.grid()

        else :
            # Write values to textfile
            filename = "shear-stresses-{0}.txt".format(project)
            #print("Writing stress data to " + filename)
            fh = None
            try :
                fh = open(filename, "w")
                L = sb.L[2] - sb.origo[2] # Initial height
                for i in range(lastfile+1):
                    # format: shear distance [mm], sigma [kPa], tau [kPa],
                    # Dilation [%]
                    fh.write("{0}\t{1}\t{2}\t{3}\n".format(xdisp[i],
                    sigma_eff[i]/1000.0,
                    tau[i]/1000.0,
                    dilation[i]))
            finally :
                if fh is not None:
                    fh.close()


    else :
        print("Visualization type '" + method + "' not understood")


    # Optional save of figure
    if (outformat != 'txt'):
        if (savefig == True):
            fig.savefig("{0}-{1}.{2}".format(project, method, outformat))
            fig.clf()
        else :
            plt.show()

def run(binary, verbose=True, hideinputfile=False):
    'Execute ``sphere`` with target binary as input'

    quiet = ""
    stdout = ""
    if (verbose == False):
        quiet = "-q"
    if (hideinputfile == True):
        stdout = " > /dev/null"
    subprocess.call("cd ..; ./sphere " + quiet + " " + binary + " " + stdout, \
            shell=True)

def torqueScriptParallel3(obj1, obj2, obj3,
        email="adc@geo.au.dk",
        email_alerts="ae",
        walltime="24:00:00",
        queue="qfermi",
        cudapath="/com/cuda/4.0.17/cuda",
        spheredir="/home/adc/code/sphere",
        workdir="/scratch"):
    ''' Create job script for the Torque queue manager for three binaries,
        executed in parallel.
        Returns the filename of the script
    '''

    filename = obj1.sid + '_' + obj2.sid + '_' + obj3.sid + '.sh'

    fh = None
    try :
        fh = open(filename, "w")

        fh.write('#!/bin/sh\n')
        fh.write('#PBS -N ' + obj1.sid + '_' + obj2.sid + '_' + obj3.sid + '\n')
        fh.write('#PBS -l nodes=1:ppn=1\n')
        fh.write('#PBS -l walltime=' + walltime + '\n')
        fh.write('#PBS -q ' + queue + '\n')
        fh.write('#PBS -M ' + email + '\n')
        fh.write('#PBS -m ' + email_alerts + '\n')
        fh.write('CUDAPATH=' + cudapath + '\n')
        fh.write('export PATH=$CUDAPATH/bin:$PATH\n')
        fh.write('export LD_LIBRARY_PATH=$CUDAPATH/lib64')
        fh.write(':$CUDAPATH/lib:$LD_LIBRARY_PATH\n')
        fh.write('echo "`whoami`@`hostname`"\n')
        fh.write('echo "Start at `date`"\n')
        fh.write('ORIGDIR=' + spheredir + '\n')
        fh.write('WORKDIR=' + workdir + "/$PBS_JOBID\n")
        fh.write('cp -r $ORIGDIR/* $WORKDIR\n')
        fh.write('cd $WORKDIR\n')
        fh.write('cmake . && make\n')
        fh.write('./sphere input/' + obj1.sid + '.bin > /dev/null &\n')
        fh.write('./sphere input/' + obj2.sid + '.bin > /dev/null &\n')
        fh.write('./sphere input/' + obj3.sid + '.bin > /dev/null &\n')
        fh.write('wait\n')
        fh.write('cp $WORKDIR/output/* $ORIGDIR/output/\n')
        fh.write('echo "End at `date`"\n')
        return filename

    finally :
        if fh is not None:
            fh.close()


def torqueScriptSerial3(obj1, obj2, obj3,
        email="adc@geo.au.dk",
        email_alerts="ae",
        walltime="24:00:00",
        queue="qfermi",
        cudapath="/com/cuda/4.0.17/cuda",
        spheredir="/home/adc/code/sphere",
        workdir="/scratch"):
    '''Create job script for the Torque queue manager for three binaries
    '''

    filename = self.sid + ".sh"
    fh = None
    try :
        fh = open(filename, "w")

        fh.write('#!/bin/sh\n')
        fh.write('#PBS -N ' + obj1.sid + '_' + obj2.sid + '_' + obj3.sid + '\n')
        fh.write('#PBS -l nodes=1:ppn=1\n')
        fh.write('#PBS -l walltime=' + walltime + '\n')
        fh.write('#PBS -q ' + queue + '\n')
        fh.write('#PBS -M ' + email + '\n')
        fh.write('#PBS -m ' + email_alerts + '\n')
        fh.write('CUDAPATH=' + cudapath + '\n')
        fh.write('export PATH=$CUDAPATH/bin:$PATH\n')
        fh.write('export LD_LIBRARY_PATH=$CUDAPATH/lib64')
        fh.write(':$CUDAPATH/lib:$LD_LIBRARY_PATH\n')
        fh.write('echo "`whoami`@`hostname`"\n')
        fh.write('echo "Start at `date`"\n')
        fh.write('ORIGDIR=' + spheredir + '\n')
        fh.write('WORKDIR=' + workdir + "/$PBS_JOBID\n")
        fh.write('cp -r $ORIGDIR/* $WORKDIR\n')
        fh.write('cd $WORKDIR\n')
        fh.write('cmake . && make\n')
        fh.write('./sphere input/' + obj1.sid + '.bin > /dev/null\n')
        fh.write('./sphere input/' + obj2.sid + '.bin > /dev/null\n')
        fh.write('./sphere input/' + obj3.sid + '.bin > /dev/null\n')
        fh.write('cp $WORKDIR/output/* $ORIGDIR/output/\n')
        fh.write('echo "End at `date`"\n')

    finally :
        if fh is not None:
            fh.close()



def status(project):
    ''' Check the status.dat file for the target project,
        and return the last file numer.
    '''

    fh = None
    try :
        filepath = "../output/{0}.status.dat".format(project)
        #print(filepath)
        fh = open(filepath)
        data = fh.read()
        #print(data)
        return int(data.split()[2])  # Return last file number
    finally :
        if fh is not None:
            fh.close()

def cleanup(spherebin):
    '''
    Removes the input/output files and images belonging to the object simulation
    ID from the ``input/``, ``output/`` and ``img_out/`` folders.

    :param spherebin: A Spherebin object
    :type spherebin: Spherebin
    '''
    subprocess.call("rm -f ../input/" + spherebin.sid + ".bin", shell=True)
    subprocess.call("rm -f ../output/" + spherebin.sid + ".*.bin", shell=True)
    subprocess.call("rm -f ../img_out/" + spherebin.sid + ".*", shell=True)

def vector_norm(ndvector):
    '''
    Returns a 1D vector of normalized values. The input array should have
    one row per particle, and three rows; one per Euclidean axis.

    :returns: A value of the velocity magnutude per particle
    :return type: numpy.array
    '''

    # Normalized velocities
    v_norm = numpy.empty(ndvector.shape[0])
    for i in range(ndvector.shape[0]):
        v_norm[i] = numpy.sqrt(ndvector[i,:].dot(ndvector[i,:]))
    return v_norm

def V_sphere(r):
    ''' Returns the volume of a sphere with radius r
    '''
    return 4.0/3.0 * math.pi * r**3.0

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
