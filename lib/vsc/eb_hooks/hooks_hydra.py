#
# Copyright 2017-2023 Vrije Universiteit Brussel
#
# This file is part of eb_hooks,
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/vub-hpc/eb_hooks
#
# All rights reserved.
#
"""
Custom EasyBuild hooks for VUB-HPC Clusters

@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
from distutils.version import LooseVersion

from easybuild.framework.easyconfig.constants import EASYCONFIG_CONSTANTS
from easybuild.tools.config import install_path

from vsc.eb_hooks.ib_modules import IB_MODULE_SOFTWARE, IB_MODULE_SUFFIX, IB_OPT_MARK, DUAL_IB_ARCHS

# permission groups for licensed software
SOFTWARE_GROUPS = {
    'ADF': 'badf',
    'AMS': 'badf',
    'CASTEP': 'bcastep',
    'COMSOL': 'bcomsol_users',  # autogroup (bcomsol, bcomsol_efremov)
    'FLUENT': 'bansys',
    'Gaussian': 'brusselall',  # site license
    'GaussView': 'brusselall',  # site license
    'Gurobi': 'brusselall',  # site license
    'Lumerical': 'bphot',
    'Mathematica': 'brusselall',  # site license
    'MATLAB': 'brusselall',  # site license
    'Q-Chem': 'bqchem',
    'QuantumATK': 'bquantumatk',
    'ReaxFF-param': 'breaxff',
    'ReaxFF-sim': 'breaxff',
    'VASP': 'bvasp',
}


def parse_hook(ec, *args, **kwargs):  # pylint: disable=unused-argument
    """Alter the parameters of easyconfigs"""

    # PMIx deps and sanity checks for munge
    if ec.name == 'PMIx':
        # Add osdependency on munge-devel
        extradep = 'munge-devel'
        ec.log.info("[parse hook] Adding OS dependency on: %s" % extradep)
        ec['osdependencies'].append(extradep)
        # Add sanity check on munge component
        ec.log.info("[parse hook] Adding sanity check on munge component")
        if LooseVersion(ec.version) >= LooseVersion('4'):
            # PMIx-v4 does not have the specific plugin for psec-munge,
            # but now it has a plugin for Slurm that links to munge
            ec['sanity_check_paths']['files'].append('lib/pmix/mca_prm_slurm.so')
        else:
            ec['sanity_check_paths']['files'].append('lib/pmix/mca_psec_munge.so')

    # InfiniBand support
    if ec.name in IB_MODULE_SOFTWARE:
        local_arch = os.getenv('VSC_ARCH_LOCAL')
        local_arch_suffix = os.getenv('VSC_ARCH_SUFFIX')

        # remove any OS dependency on libverbs in non-IB nodes
        if not local_arch_suffix == IB_MODULE_SUFFIX:
            pkg_ibverbs = EASYCONFIG_CONSTANTS['OS_PKG_IBVERBS_DEV'][0]
            ec['osdependencies'] = [d for d in ec['osdependencies'] if d != pkg_ibverbs]
            ec.log.info("[parse hook] OS dependencies on non-IB system: %s", ec['osdependencies'])

        # archs with IB/non-IB nodes get the IB version in a versionsuffix
        if local_arch in DUAL_IB_ARCHS and local_arch_suffix == IB_MODULE_SUFFIX:
            ec['versionsuffix'] += IB_MODULE_SUFFIX
            ec.log.info("[parse hook] Appended IB suffix to version string: %s", ec['versionsuffix'])

    if ec.name == 'Gurobi':
        # use centrally installed Gurobi license file, and don't copy to installdir
        ec['license_file'] = '/apps/brussel/licenses/gurobi/gurobi.lic'
        ec.log.info(f"[parse hook] Set parameter license_file: {ec['license_file']}")
        ec['copy_license_file'] = False
        ec.log.info(f"[parse hook] Set parameter copy_license_file: {ec['copy_license_file']}")

    if ec.name == 'MATLAB':
        ec['license_file'] = '/apps/brussel/licenses/matlab/network.lic'
        ec.log.info(f"[parse hook] Set parameter license_file: {ec['license_file']}")
        # replace copy of license file in install dir with link to original license
        ec['postinstallcmds'] = [f'ln -sfb {ec["license_file"]} %(installdir)s/licenses/']
        ec.log.info(f"[parse hook] Set parameter postinstallcmds: {ec['postinstallcmds']}")

    if ec.name in SOFTWARE_GROUPS:
        ec['group'] = SOFTWARE_GROUPS[ec.name]
        ec.log.info(f"[parse hook] Set parameter group: {ec['group']}")


def pre_configure_hook(self, *args, **kwargs):  # pylint: disable=unused-argument
    """Hook at pre-configure level to alter configopts"""

    # PMIx settings:
    # - build with munge support to work with Slurm
    # - disable per-user configuration files to save disk accesses during job start-up
    if self.name == 'PMIx':
        self.log.info("[pre-configure hook] Enable munge support")
        self.cfg.update('configopts', "--with-munge")
        if LooseVersion(self.version) >= LooseVersion('2'):
            self.log.info("[pre-configure hook] Disable per-user configuration")
            self.cfg.update('configopts', "--disable-per-user-config-files")

    # InfiniBand support:
    if self.name in IB_MODULE_SOFTWARE:
        local_arch_suffix = os.getenv('VSC_ARCH_SUFFIX')
        ec_param = IB_MODULE_SOFTWARE[self.name][0]

        # convert any non-list parameters to a list
        if ec_param == 'configopts':
            ec_config = self.cfg['configopts'].split(' ')
        else:
            ec_config = self.cfg[ec_param]

        # clean any settings about IB
        ib_free_config = [opt for opt in ec_config if not any(mark in opt for mark in IB_OPT_MARK)]

        # update IB settings
        if local_arch_suffix == IB_MODULE_SUFFIX:
            self.log.info("[pre-configure hook] Enabling verbs in %s", self.name)
            ib_opt = IB_MODULE_SOFTWARE[self.name][1]
        else:
            self.log.info("[pre-configure hook] Disabling verbs in %s", self.name)
            ib_opt = IB_MODULE_SOFTWARE[self.name][2]

        ib_config = ib_free_config + [ib_opt]

        # consolidate changes
        if ec_param == 'configopts':
            self.cfg['configopts'] = ' '.join(ib_config)
        else:
            self.cfg[ec_param] = ib_config

        self.log.info("[pre-configure hook] Updated '%s': %s", ec_param, self.cfg[ec_param])


def pre_module_hook(self, *args, **kwargs):  # pylint: disable=unused-argument
    """Hook at pre-module level to alter module files"""

    # Must be done this way, updating self.cfg['modextravars']
    # directly doesn't work due to templating.
    en_templ = self.cfg.enable_templating
    self.cfg.enable_templating = False

    # MPI settings:
    if self.name == 'OpenMPI':
        # use pbsdsh instead of ssh for OpenMPI in Torque
        # more info: https://projects.cc.vub.ac.be/issues/2933
        self.log.info("[pre-module hook] Set MPI bootstrap in Torque")
        pbs_env = [("OMPI_MCA_plm_rsh_agent", "pbsdsh")]

        # set MPI communication type in Slurm (default is none)
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/4706
        slurm_mpi_type = None
        if LooseVersion(self.version) >= '3.0.0':
            slurm_mpi_type = 'pmix'
        elif LooseVersion(self.version) >= '2.1.0':
            slurm_mpi_type = 'pmi2'

        if slurm_mpi_type:
            self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
            self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

        # map processes to cores to avoid torque-NUMA issue for OpenMPI version >= 4.0.3
        # this is a temporary workaround until we have a proper fix
        # more info: https://projects.cc.vub.ac.be/issues/3068
        if LooseVersion(self.version) >= '4.0.3':
            self.log.info("[pre-module hook] Set OMPI_MCA_rmaps_base_mapping_policy=core for Torque")
            pbs_env.append(("OMPI_MCA_rmaps_base_mapping_policy", "core"))

        modlua_setenv = ['setenv("%s", "%s")' % (e, v) for (e, v) in pbs_env]
        self.cfg['modluafooter'] = """
if ( os.getenv("PBS_JOBID") and not os.getenv("SLURM_JOB_ID") ) then
    %s
end
""" % '\n    '.join(modlua_setenv)

    if self.name == 'impi':
        # - use PMI1/2 implementation from Slurm
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7192
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7588

        # use PMI1 by default (works with older versions)
        slurm_mpi_type = None
        intel_mpi = {
            'pmi_var': 'I_MPI_PMI2',
            'pmi_set': 'no',
            'pmi_lib': '/usr/lib64/slurmpmi/libpmi.so',
        }

        if LooseVersion(self.version) >= '2019.7':
            # Intel MPI v2019 supports PMI2 with I_MPI_PMI=pmi2, but it only atually works since v2019.7
            # see https://bugs.schedmd.com/show_bug.cgi?id=6727
            intel_mpi['pmi_var'] = 'I_MPI_PMI'
            intel_mpi['pmi_set'] = 'pmi2'
            intel_mpi['pmi_lib'] = '/usr/lib64/slurmpmi/libpmi2.so'
            slurm_mpi_type = 'pmi2'
        elif LooseVersion(self.version) >= '2019.0':
            # use PMI1 with this buggy releases of Intel MPI
            # see https://bugs.schedmd.com/show_bug.cgi?id=6727
            intel_mpi['pmi_var'] = 'I_MPI_PMI'
            intel_mpi['pmi_set'] = 'pmi1'
        elif LooseVersion(self.version) >= '2018.0':
            # Intel MPI v2018 supports PMI2 with I_MPI_PMI2=yes
            intel_mpi['pmi_set'] = 'yes'
            intel_mpi['pmi_lib'] = '/usr/lib64/slurmpmi/libpmi2.so'
            slurm_mpi_type = 'pmi2'

        # - use pbsdsh instead of ssh for Intel MPI in Torque
        # more info: https://projects.cc.vub.ac.be/issues/2933
        self.log.info("[pre-module hook] Set MPI bootstrap for Torque and Slurm")
        self.cfg['modluafooter'] = """
if ( os.getenv("SLURM_JOB_ID") ) then
    setenv("I_MPI_HYDRA_BOOTSTRAP", "slurm")
    setenv("I_MPI_PIN_RESPECT_CPUSET", "0")
    setenv("I_MPI_PMI_LIBRARY", "%(pmi_lib)s")
    setenv("%(pmi_var)s", "%(pmi_set)s")
elseif ( os.getenv("PBS_JOBID") ) then
    setenv("I_MPI_HYDRA_BOOTSTRAP", "pbsdsh")
end
""" % intel_mpi

        # set MPI communication type in Slurm (default is none, which works for PMI1)
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7192
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7588
        if slurm_mpi_type:
            self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
            self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

    # set the maximum heap memory for Java applications to 80% of memory allocated to the job
    # more info: https://projects.cc.vub.ac.be/issues/2940
    if self.name == 'Java':
        self.log.info("[pre-module hook] Set max heap memory in Java module")
        self.cfg['modluafooter'] = """
local mem = get_avail_memory()
if mem then
    setenv("JAVA_TOOL_OPTIONS",  "-Xmx" .. math.floor(mem*0.8))
end
"""

    # set MATLAB Runtime Component Cache folder to a local temp dir
    # this cache directory lies in $HOME by default, which cause binaries compiled with MCC to hang
    if self.name == 'MATLAB':
        self.log.info("[pre-module hook] Set MATLAB Runtime Component Cache folder")
        self.cfg['modluafooter'] = """
setenv("MCR_CACHE_ROOT", os.getenv("TMPDIR") or pathJoin("/tmp", os.getenv("USER")))
"""

    # Set single MODULEPATH in JupyterHub
    if self.name == 'JupyterHub':
        mod_install_path = os.path.join(install_path('mod'), "all")
        self.log.info("[parse hook] Setting single MODULEPATH on module load to: %s", mod_install_path[-9:])

        # cannot know MODULEPATH in advance for archs with IB variants, use environment at load time
        local_arch = os.getenv('VSC_ARCH_LOCAL') + os.getenv("VSC_ARCH_SUFFIX")
        archless_path = ['"%s"' % p for p in mod_install_path.split(local_arch)]
        if len(archless_path) > 1:
            archless_path.insert(1, 'os.getenv("VSC_ARCH_LOCAL") .. os.getenv("VSC_ARCH_SUFFIX")')

        self.cfg['modluafooter'] = """
-- restrict MODULEPATH to current software generation
if ( mode() ~= "spider" ) then
    pushenv("MODULEPATH", "/etc/modulefiles/vsc")
    prepend_path("MODULEPATH", pathJoin(%s))
end
""" % ", ".join(archless_path)

    # set COMSOL licenses
    if self.name == 'COMSOL':
        self.cfg['modluafooter'] = """
if userInGroup("bcomsol") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License.dat")
elseif userInGroup("bcomsol_efremov") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License_efremov.dat")
end
"""

    # print info about BUSCO database
    if self.name == 'BUSCO':
        if LooseVersion(self.version) >= '5.0.0':
            self.cfg['modloadmsg'] = """
BUSCO v5 databases are located in /databases/bio/BUSCO-5. Use local DBs with command:
`busco --offline --download_path /databases/bio/BUSCO-5 ...`
"""

    # add links to our documentation for software covered in
    # https://hpc.vub.be/docs/software/usecases/
    doc_url = 'https://hpc.vub.be/docs/software/usecases/'
    doc_app = ['MATLAB', 'R', 'Gaussian', 'GaussView', 'matplotlib', ('CESM-deps', 'cesm-cime'), 'GAP', 'Mathematica',
               'Stata', 'GROMACS', 'CP2K', 'PyTorch', 'ORCA', 'SRA-Toolkit', 'AlphaFold', 'OpenFold', 'GAMESS-US']

    # generate links for documented apps
    app_anchors = [(app, app.lower()) if isinstance(app, str) else app for app in doc_app]
    app_links = {app: '#'.join([doc_url, anchor]) for (app, anchor) in app_anchors}

    if self.name in app_links:
        # update usage section
        usage_info = {'app': self.name, 'link': app_links[self.name]}
        usage_msg = """
Specific usage instructions for %(app)s are available in VUB-HPC documentation:
%(link)s
""" % usage_info
        self.cfg['usage'] = usage_msg + self.cfg['usage'] if self.cfg['usage'] else usage_msg
        # update documentation links
        if self.cfg['docurls']:
            self.cfg['docurls'].append(usage_info['link'])
        else:
            self.cfg['docurls'] = [usage_info['link']]

    self.cfg.enable_templating = en_templ
