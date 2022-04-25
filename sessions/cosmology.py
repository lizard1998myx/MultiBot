from ..utils import image_filename
from .argument import ArgSession, Argument
from ..responses import ResponseMsg, ResponseImg
import numpy as np
from scipy import integrate
import matplotlib.pyplot as plt
import traceback

# 2021-12-14 迁移


class CosmoPlotSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '宇宙学计算器'
        self.description = '计算一些常见的宇宙学量'
        self._max_delta = 60
        self.extend_commands = ['宇宙学', 'cosmo']
        self.arg_list = [Argument(key='density-fig', alias_list=['-f1'],
                                  help_text='density curve'),
                         Argument(key='distance-fig', alias_list=['-f2'],
                                  help_text='distance curve'),
                         Argument(key='jeans-fig', alias_list=['-f3'],
                                  help_text='gas Jeans mass curve'),
                         Argument(key='growth-fig', alias_list=['-f4'],
                                  help_text='linear growth factor curve'),
                         Argument(key='zmin', alias_list=['-zmin'],
                                  get_next=True, default_value=0,
                                  help_text='min redshift (0)'),
                         Argument(key='zmax', alias_list=['-zmax'],
                                  get_next=True, default_value=1000,
                                  help_text='max redshift (1000)'),
                         Argument(key='h0', alias_list=['-h'],
                                  get_next=True, default_value=0.7,
                                  help_text='hubble param (0.7)'),
                         Argument(key='m0', alias_list=['-m'],
                                  get_next=True, default_value=0.3,
                                  help_text='Omega_m0 (0.3)'),
                         Argument(key='r0', alias_list=['-r'],
                                  get_next=True, default_value=8.5e-5,
                                  help_text='Omega_r0 (8.5e-5)'),
                         Argument(key='l0', alias_list=['-l'],
                                  get_next=True, default_value=0.7,
                                  help_text='Omega_l0 (0.7)'),
                         Argument(key='no-flat', alias_list=['-nf'],
                                  help_text='non flat universe (disabled by default)'),
                         Argument(key='EdS', alias_list=['-eds'],
                                  help_text='use EdS universe'),
                         Argument(key='LCDM', alias_list=['-lcdm'],
                                  help_text='use LCDM universe'),
                         ]
        self.default_arg = self.arg_list[0]
        self.detail_description = 'example: cosmo -m 0.8 -r 0. -l 0.2 -h 0.6 -zmax 5000 -f2'
        self.this_first_time = True

    def internal_handle(self, request):
        if self.this_first_time:
            self.this_first_time = False
            if self.arg_dict['EdS'].called:
                self.arg_dict['m0'].value = 1.
                self.arg_dict['r0'].value = 0.
                self.arg_dict['l0'].value = 0.
                flat = True
            elif self.arg_dict['LCDM'].called:
                self.arg_dict['m0'].value = 0.3
                self.arg_dict['r0'].value = 8.5e-5
                self.arg_dict['l0'].value = 0.7
                flat = True
            else:
                flat = not self.arg_dict['no-flat'].called
            try:
                cosmo = ParameterCalculator()
                cosmo.O_m0 = float(self.arg_dict['m0'].value)
                cosmo.O_l0 = float(self.arg_dict['l0'].value)
                cosmo.O_r0 = float(self.arg_dict['r0'].value)
                cosmo.h0 = float(self.arg_dict['h0'].value)
                cosmo.set_k0(flat=flat)
                plot_kwargs = {'cosmo': cosmo,
                               'zmin': float(self.arg_dict['zmin'].value),
                               'zmax': float(self.arg_dict['zmax'].value)}
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】参数不合法')
        else:
            try:
                i_fig = int(request.msg)
                if i_fig == 1:
                    self.arg_dict['density-fig'].called = True
                elif i_fig == 2:
                    self.arg_dict['distance-fig'].called = True
                elif i_fig == 3:
                    self.arg_dict['jeans-fig'].called = True
                elif i_fig == 4:
                    self.arg_dict['growth-fig'].called = True
                else:
                    raise ValueError
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】参数不合法')

        responses = []
        for fig_type in ['density', 'distance', 'jeans', 'growth']:
            if self.arg_dict[f'{fig_type}-fig'].called:
                filename = image_filename(header=f'Cosmo_{fig_type}', abs_path=True)
                plot_func = eval(f'PlotFunc.{fig_type}')
                try:
                    plot_func(filename=filename, **plot_kwargs)
                    responses.append(ResponseImg(file=filename))
                except Exception:
                    traceback.print_exc()
                    responses.append(ResponseMsg(f'【{self.session_type}】{fig_type}-fig 生成失败'))

        if len(responses) == 0:
            return ResponseMsg(f'【{self.session_type}】请输入想画图的类型：\n'
                               f'1. 物质密度\n'
                               f'2. 宇宙学距离\n'
                               f'3. 气体的Jeans质量\n'
                               f'4. 线性增长因子与EdS、LCDM宇宙的比较')
        else:
            self.deactivate()
            return responses


class PhysicalConstants:
    def __init__(self):
        self.h_p = 6.626e-34  # Planck constant [J*s]
        self.c = 3e8  # speed of light [m/s]
        self.k_b = 1.381e-23  # Boltzmann constant [J/K]
        self.G = 6.673e-11  # Newton Gravity constant [N*m^2/kg^2]
        self.pc = 3.0857e16  # parsec [meters]
        self.year = 3600 * 24 * 365.25  # year [seconds]
        self.ly = self.c * self.year  # light year [m]
        self.m_p = 1.6726e-27  # mass of proton [kg]
        self.m_sun = 1.989e30  # solar mass [kg]

    def h2SI(self, h):  # h: unit *100 km*s^-1*Mpc^-1
        return h * 100 * 1e3 / (1e6 * self.pc)

    def h2pc(self, h_SI):
        return h_SI * 1e6 * self.pc / (100 * 1e3)

    def t2year(self, t_s):
        return t_s / self.year


class DensityCalculator(PhysicalConstants):
    def __init__(self):
        PhysicalConstants.__init__(self)

    def rho_radiation(self, T=2.725):  # unit Kelvin
        stefan = 2 * np.pi ** 5 * self.k_b ** 4 / (15 * self.c ** 2 * self.h_p ** 3)
        return 4 * stefan * T ** 4 / self.c ** 3

    def rho_critical(self, h):  # h: unit *100 km*s^-1*Mpc^-1
        return 3 * self.h2SI(h) ** 2 / (8 * np.pi * self.G)

    def jeans_length(self, c_s, rho):  # unit m/s & kg/m3
        return c_s * (np.pi / (self.G * rho)) ** 0.5

    def jeans_length_gas(self, rho, T):  # unit kg/m3 & K
        c_s = (5 * self.k_b * T / (3 * self.m_p))
        return self.jeans_length(c_s=c_s, rho=rho)

    def jeans_mass(self, rho, l_j):  # unit kg/m3 & m
        return np.pi * rho * l_j ** 3 / 6


class ParameterCalculator(PhysicalConstants):
    def __init__(self):
        PhysicalConstants.__init__(self)
        self.O_m0 = 0.25
        self.O_r0 = 0.
        self._O_k0 = 0.  # pho_k = -K
        self.O_l0 = 0.75
        self.a0 = 1.
        self.h0 = 0.673

    def kai2r(self, kai):
        if self._O_k0 == 0:
            return kai
        elif self._O_k0 > 0:  # K = -1
            return np.sinh(kai)
        else:  # K = +1
            return np.sin(kai)

    def _E(self, z):
        return np.sqrt(self.O_r0 * (1 + z) ** 4 + self.O_m0 * (1 + z) ** 3 + self._O_k0 * (1 + z) ** 2 + self.O_l0)

    def h(self, z):  # Hubble parameter at redshift z
        return self.h0 * self._E(z)

    def t_back(self, z):  # look back time, in seconds
        return integrate.quad(lambda x: 1 / ((1 + x) * self.h2SI(self.h(x))), 0, z)[0]

    def age(self, z):  # integrate dz/((1+z)*H(z)) from z to infinity
        return integrate.quad(lambda x: 1 / ((1 + x) * self.h2SI(self.h(x))), z, np.inf)[0]

    def growth_factor(self, z):  # growing mode of perturbation (fluid) - see 4.7.2 of GalForm&Evo
        return self.h(z) * integrate.quad(lambda x: (1 + x) / self._E(x) ** 3, z, np.inf)[0]

    def set_k0(self, flat=True):
        if flat:
            self._O_k0 = 0
            self.a0 = 1.
        else:
            self._O_k0 = 1. - self.O_m0 - self.O_r0 - self.O_l0
            self.a0 = np.sqrt(self.c ** 2 / (self.h2SI(self.h0) * np.abs(self._O_k0)))

    def get_distance_calculator(self):
        dcal = DistanceCalculator()
        dcal.O_m0 = self.O_m0
        dcal.O_r0 = self.O_r0
        dcal.O_k0 = self._O_k0
        dcal.O_l0 = self.O_l0
        dcal.a0 = self.a0
        dcal.h0 = self.h0
        return dcal


class DistanceCalculator(ParameterCalculator):
    def __init__(self):  # all SI
        ParameterCalculator.__init__(self)

    def comoving_distance(self, z, z0=0.):  # integrate c*dz/a0*H(z) from 0 to z
        return integrate.quad(lambda x: self.c / (self.h2SI(self.h(x)) * self.a0), z0, z)[0]

    def proper_distance(self, z, dc=None):
        if dc is None:
            dc = self.comoving_distance(z)
        return self.a0 * dc

    def angular_distance(self, z, dc=None):
        if dc is None:
            dc = self.comoving_distance(z)
        return self.a0 * self.kai2r(dc) / (1 + z)

    def luminosity_distance(self, z, dc=None):
        if dc is None:
            dc = self.comoving_distance(z)
        return self.a0 * self.kai2r(dc) * (1 + z)

    def particle_horizon(self):
        return self.comoving_distance(np.inf)

    def event_horizon(self):
        return self.comoving_distance(z0=-1 * np.inf, z=0)


class GravWaveCalculator(PhysicalConstants):
    def __init__(self):
        PhysicalConstants.__init__(self)

    @staticmethod
    def mu_mass(m1, m2):
        return m1 * m2 / (m1 + m2)


class PlotFunc:
    # 物质密度
    @staticmethod
    def density(cosmo, zmin, zmax, filename):
        pcal = cosmo
        dcal = DensityCalculator()
        dens_c_0 = dcal.rho_critical(h=pcal.h0)
        dens_r_0 = pcal.O_r0 * dens_c_0
        dens_m_0 = pcal.O_m0 * dens_c_0
        dens_l_0 = pcal.O_l0 * dens_c_0

        z_rm = (dens_m_0 / dens_r_0) - 1
        z_lm = (dens_l_0 / dens_m_0) ** (1 / 3) - 1

        pcal.O_r0 = dens_r_0 / dens_c_0
        lg_z_plus_1 = np.arange(np.log10(zmin + 1), np.log10(zmax + 1), 0.01)
        z_plus_1 = 10 ** lg_z_plus_1
        rm = dens_m_0 * z_plus_1 ** 3
        rl = dens_l_0 * z_plus_1 ** 0
        rr = dens_r_0 * z_plus_1 ** 4
        ymax = np.max([rm, rl, rr])*10
        ymin = np.min([rm, rl, rr])/10
        fig, ax = plt.subplots()
        ax.plot(z_plus_1, rm, label='matter')
        ax.plot(z_plus_1, rl, label='dark energy')
        ax.plot(z_plus_1, rr, label='radiation')
        ax.vlines(z_lm + 1, ymin, ymax, linestyles='--')
        ax.vlines(z_rm + 1, ymin, ymax, linestyles='--')
        ax.set(title='Cosmology Density', ylabel=r'Density / $\rm{kg\times m^{-3}}$', xlabel='1+z',
               xscale='log', yscale='log', xlim=(zmin+1, zmax+1), ylim=(ymin, ymax))
        ax.legend()
        ax.grid()
        fig.tight_layout()
        plt.savefig(filename)

    # 宇宙学距离
    @staticmethod
    def distance(cosmo, zmin, zmax, filename):
        dcal = cosmo.get_distance_calculator()
        distances = {r"$\rm{D_P}$": dcal.proper_distance,
                     r"$\rm{D_A}$": dcal.angular_distance,
                     r"$\rm{D_L}$": dcal.luminosity_distance}
        lg_z_plus_1 = np.arange(np.log10(zmin + 1), np.log10(zmax + 1), 0.01)
        z_plus_1 = 10 ** lg_z_plus_1
        fig, ax = plt.subplots()
        for label, func in distances.items():
            ax.plot(z_plus_1, np.array(list(map(func, z_plus_1 - 1))) / dcal.pc, label=label)
        ax.set(title='Cosmology Distance', ylabel=r"Distance / pc", xlabel='1+z', xscale='log', yscale='log')
        ax.legend()
        ax.grid()
        fig.tight_layout()
        plt.savefig(filename)

    # 气体Jeans质量
    @staticmethod
    def jeans(cosmo, zmin, zmax, filename):
        O_b0 = 0.0484
        dcal = DensityCalculator()
        dens_c_0 = dcal.rho_critical(h=cosmo.h0)
        dens_b_0 = O_b0 * dens_c_0

        lg_z_plus_1 = np.arange(np.log10(zmin + 1), np.log10(zmax + 1), 0.01)
        z_plus_1 = 10 ** lg_z_plus_1
        rho = dens_b_0 * z_plus_1 ** 3
        temp = 1e8
        l_j = dcal.jeans_length_gas(rho=rho, T=temp)
        m_j = dcal.jeans_mass(rho=rho, l_j=l_j) / dcal.m_sun
        fig, ax = plt.subplots()
        ax.plot(z_plus_1, m_j)
        ax.set(title='gas Jeans mass (O_b0=0.0484)', ylabel="Jeans Mass [$M_\odot$]", xlabel='1+z',
               xscale='log', yscale='log')
        ax.grid()
        fig.tight_layout()
        plt.savefig(filename)

    # 两种宇宙学的linear growth rate
    @staticmethod
    def growth(cosmo, zmin, zmax, filename):
        cosmo_EdS = ParameterCalculator()
        cosmo_EdS.O_m0 = 1.
        cosmo_EdS.O_l0 = 0.
        cosmo_EdS.O_r0 = 0.
        cosmo_EdS.h0 = cosmo.h0

        cosmo_LCDM = ParameterCalculator()
        cosmo_LCDM.O_m0 = 0.3
        cosmo_LCDM.O_l0 = 0.7
        cosmo_LCDM.O_r0 = 8.5e-5
        cosmo_LCDM.h0 = cosmo.h0

        lg_z_plus_1 = np.arange(np.log10(zmin + 1), np.log10(zmax + 1), 0.01)
        z_plus_1 = 10 ** lg_z_plus_1

        fig, ax = plt.subplots()
        for label, universe in {'EdS': cosmo_EdS, 'LCDM': cosmo_LCDM, 'your': cosmo}.items():
            D_0 = universe.growth_factor(0.)
            ax.plot(z_plus_1, np.array(list(map(universe.growth_factor, z_plus_1 - 1))) / D_0, label=label)

        ax.set(title='D(z) in cosmo', ylabel="linear growth factor D(z)", xlabel='1+z', xscale='log')
        # plt.yscale('log')
        ax.legend()
        ax.grid()
        fig.tight_layout()
        plt.savefig(filename)
