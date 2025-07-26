#
# Copyright 2017-2024 Vrije Universiteit Brussel
# All rights reserved.
#
# This file is part of build_tools (https://github.com/vub-hpc/build_tools),
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
##
"""
Custom EasyBuild hooks for VUB-HPC Clusters

@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import re
import sys
import time

from flufl.lock import Lock, TimeOutError, NotLockedError

from easybuild.framework.easyconfig.constants import EASYCONFIG_CONSTANTS
from easybuild.framework.easyconfig.easyconfig import letter_dir_for, get_toolchain_hierarchy
from easybuild.tools import LooseVersion
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.config import build_option, ConfigurationVariables, source_paths, update_build_option
from easybuild.tools.filetools import mkdir
from easybuild.tools.hooks import SANITYCHECK_STEP

from build_tools.clusters import ARCHS
from build_tools.ib_modules import IB_MODULE_SOFTWARE, IB_MODULE_SUFFIX, IB_OPT_MARK

# user groups for licensed software
SOFTWARE_GROUPS = {
    'ABAQUS': 'babaqus',
    'ADF': 'badf',
    'AMS': 'badf',
    'ANSYS': 'bansys',
    'CASTEP': 'bcastep',
    'COMSOL': 'bcomsol_users',  # autogroup (bcomsol, bcomsol_efremov)
    'CRYSTAL': 'bcrystal',  # autogroup (bcrystal-algc)
    'FLUENT': 'bansys',
    'FreeSurfer': 'bfreesurfer',
    'FUNAERO': 'bfunaero',
    'Gaussian': 'brusselall',  # site license
    'GaussView': 'brusselall',  # site license
    'Gurobi': 'brusselall',  # site license
    'Lumerical': 'bphot',
    'Mathematica': 'brusselall',  # site license
    'MATLAB': 'brusselall',  # site license
    'Morfeo': 'bmorfeo',
    'Q-Chem': 'bqchem',
    'QuantumATK': 'bquantumatk',
    'ReaxFF': 'breaxff',
    'Stata': 'brusselall',  # site license
    'VASP': {r'^6\.': 'bvasp6', r'^5\.': 'bvasp'},
}

GPU_ARCHS = [x for (x, y) in ARCHS.items() if y['partition']['gpu']]

LOCAL_ARCH = os.getenv('VSC_ARCH_LOCAL')
LOCAL_ARCH_SUFFIX = os.getenv('VSC_ARCH_SUFFIX')
LOCAL_ARCH_FULL = f'{LOCAL_ARCH}{LOCAL_ARCH_SUFFIX}'

VALID_TOOLCHAINS = {
    '2024a': {
        'toolchains': ['foss', 'intel', 'gomkl', 'gimkl', 'gimpi'],
        'subdir': '2024a',
    },
    '25.1': {
        'toolchains': ['nvidia-compilers', 'NVHPC'],
        'subdir': '2024a',
    },
}
VALID_MODULES_SUBDIRS = ['system', '2024a']

SUBDIR_MODULES_BWRAP = '.modules_bwrap'
SUFFIX_MODULES_PATH = 'collection'
SUFFIX_MODULES_SYMLINK = 'all'

##################
# MODULE FOOTERS #
##################

INTEL_MPI_MOD_FOOTER = """
if ( os.getenv("SLURM_JOB_ID") ) then
    setenv("I_MPI_HYDRA_BOOTSTRAP", "slurm")
    setenv("I_MPI_PIN_RESPECT_CPUSET", "0")
    setenv("I_MPI_PMI_LIBRARY", "{pmi_lib}")
    setenv("I_MPI_PMI", "{pmi_set}")
end
"""
JAVA_MOD_FOOTER = """
local mem = get_avail_memory()
if mem then
    setenv("JAVA_TOOL_OPTIONS",  "-Xmx" .. math.floor(mem*0.8))
end
"""
GPU_DUMMY_MOD_FOOTER = """
if mode() == "load" and not os.getenv("BUILD_TOOLS_LOAD_DUMMY_MODULES") then
    LmodError([[
This module is only available on nodes with a GPU.
Jobs can request GPUs with the command 'srun --gpus-per-node=1' or 'sbatch --gpus-per-node=1'.

More information in the VUB-HPC docs:
https://hpc.vub.be/docs/job-submission/gpu-job-types/#gpu-jobs
    ]])
end
"""


def get_group(name, version):
    """
    get the user group for licensed software
    returns None if there no group defined
    """
    group = None
    if name in SOFTWARE_GROUPS:
        if isinstance(SOFTWARE_GROUPS[name], str):
            group = SOFTWARE_GROUPS[name]
        else:
            for regex, grp in SOFTWARE_GROUPS[name].items():
                if re.search(regex, version):
                    group = grp
                    break
            if group is None:
                raise EasyBuildError(f"No group defined for version {version} of licensed software {name}")
    return group


def get_tc_versions():
    " build dict of valid (sub)toolchain-version combinations per valid generation "

    # temporarily disable hooks to avoid infinite recursion when calling get_toolchain_hierarchy()
    hooks = build_option('hooks')
    update_build_option('hooks', None)

    tc_versions = {}
    for tcgen, tcgen_spec in VALID_TOOLCHAINS.items():
        tcgen_versions = []
        for tc_name in tcgen_spec['toolchains']:
            try:
                tcgen_versions.extend(get_toolchain_hierarchy({'name': tc_name, 'version': tcgen}))
            except EasyBuildError:
                # skip if no easyconfig found for toolchain-version
                pass
        tc_versions[tcgen] = {
            'toolchains': tcgen_versions,
            'subdir': tcgen_spec['subdir'],
        }

    update_build_option('hooks', hooks)
    return tc_versions


def calc_tc_gen_subdir(name, version, tcname, tcversion, easyblock):
    """
    calculate the toolchain generation subdir
    return False if not valid
    """
    name_version = {'name': name, 'version': version}
    toolchain = {'name': tcname, 'version': tcversion}
    software = [name, version, tcname, tcversion, easyblock]

    tc_versions = get_tc_versions()

    # (software with) valid (sub)toolchain-version combination
    for tcgen, tcgen_spec in tc_versions.items():
        if toolchain in tcgen_spec['toolchains'] or name_version in tcgen_spec['toolchains']:
            tcgen_subdir = tcgen_spec['subdir']
            log_msg = f"Determined toolchain generation subdir '{tcgen_subdir}' for {software}"
            return tcgen_subdir, log_msg

    # invalid toolchains
    # all toolchains have 'system' toolchain, so we need to handle the invalid toolchains separately
    # all toolchains have 'Toolchain' easyblock, so checking the easyblock is sufficient
    if easyblock == 'Toolchain':
        log_msg = f"Invalid toolchain {name} for {software}"
        return False, log_msg

    # software with 'system' toolchain: return 'system'
    if tcname == 'system':
        tcgen_subdir = 'system'
        log_msg = f"Determined toolchain '{tcgen_subdir}' for {software}"
        return tcgen_subdir, log_msg

    log_msg = f"Invalid toolchain {tcname} and/or toolchain version {tcversion} for {software}"
    return False, log_msg


def is_gpu_software(ec):
    "determine if it is a GPU-only installation"
    gpu_components = ['CUDA']
    gpu_toolchains = ['nvidia-compilers', 'NVHPC']

    is_gpu_package = ec.name in gpu_components or ec.name in gpu_toolchains
    needs_gpu_toolchain = ec.toolchain.name in gpu_toolchains
    needs_gpu_component = any([x in ec['versionsuffix'] for x in gpu_components])

    return  is_gpu_package or needs_gpu_toolchain or needs_gpu_component


def update_moduleclass(ec):
    "update the moduleclass of an easyconfig to <tc_gen>/all"
    tc_gen, log_msg = calc_tc_gen_subdir(
        ec.name, ec.version, ec.toolchain.name, ec.toolchain.version, ec.easyblock
    )

    if not tc_gen:
        raise EasyBuildError("[parse hook] " + log_msg)

    ec.log.info("[parse hook] " + log_msg)

    ec['moduleclass'] = os.path.join(tc_gen, SUFFIX_MODULES_SYMLINK)

    ec.log.info("[parse hook] updated moduleclass to %s", ec['moduleclass'])


def acquire_fetch_lock(self):
    " acquire fetch lock "
    source_path = source_paths()[0]
    full_source_path = os.path.join(source_path, letter_dir_for(self.name), self.name)
    lock_name = full_source_path.replace('/', '_') + '.lock'

    lock_dir = os.path.join(source_path, '.locks')
    mkdir(lock_dir, parents=True)

    wait_time = 0
    wait_interval = 60
    wait_limit = 3600

    lock = Lock(os.path.join(lock_dir, lock_name), lifetime=wait_limit, default_timeout=1)
    self.fetch_hook_lock = lock

    while True:
        try:
            # try to acquire the lock
            lock.lock()
            self.log.info("[pre-fetch hook] Lock acquired: %s", lock.lockfile)
            break

        except TimeOutError as err:
            if wait_time >= wait_limit:
                error_msg = "[pre-fetch hook] Maximum wait time for lock %s to be released reached: %s sec >= %s sec"
                raise EasyBuildError(error_msg, lock.lockfile, wait_time, wait_limit) from err

            msg = "[pre-fetch hook] Lock %s held by another build, waiting %d seconds..."
            self.log.debug(msg, lock.lockfile, wait_interval)
            time.sleep(wait_interval)
            wait_time += wait_interval


def release_fetch_lock(self):
    " release fetch lock "
    lock = self.fetch_hook_lock
    try:
        lock.unlock()
        self.log.info("[post-fetch hook] Lock released: %s", lock.lockfile)

    except NotLockedError:
        self.log.warning("[post-fetch hook] Could not release lock %s: was already released", lock.lockfile)


def parse_hook(ec, *args, **kwargs):  # pylint: disable=unused-argument
    """Alter build options and easyconfig parameters"""

    if not ec['moduleclass'].endswith(f'/{SUFFIX_MODULES_SYMLINK}'):
        update_moduleclass(ec)

    # keep previous installation directory for bwrap (only for the vsc bot)
    if os.getenv('BWRAP', '') == '1':
        ec['keeppreviousinstall'] = True
        ec.log.info("[parse hook] Set keeppreviousinstall to %s for bwrap", ec['keeppreviousinstall'])

    # disable robot for bwrap (only when building with build_tools)
    # must be done in a hook in case robot is set in an easystack, which takes precedence over cmd line options
    subdir_modules = ConfigurationVariables()['subdir_modules']
    robot = build_option('robot')
    if subdir_modules == SUBDIR_MODULES_BWRAP and robot is not None:
        update_build_option('robot', None)
        ec.log.warning("[parse hook] Disabled robot for bwrap")

    # PMIx deps and sanity checks for munge
    if ec.name == 'PMIx':
        # Add osdependency on munge-devel
        extradep = 'munge-devel'
        ec.log.info("[parse hook] Adding OS dependency on: %s", extradep)
        ec['osdependencies'].append(extradep)
        # Add sanity check on munge component
        ec.log.info("[parse hook] Adding sanity check on munge component")
        # PMIx-v4 does not have the specific plugin for psec-munge,
        # but now it has a plugin for Slurm that links to munge
        if LooseVersion(ec.version) >= LooseVersion('4.2'):
            pmix_slurm_lib = 'lib/pmix/pmix_mca_prm_slurm.so'
        elif LooseVersion(ec.version) >= LooseVersion('4.0'):
            pmix_slurm_lib = 'lib/pmix/mca_prm_slurm.so'
        else:
            pmix_slurm_lib = 'lib/pmix/mca_psec_munge.so'

        ec['sanity_check_paths']['files'].append(pmix_slurm_lib)

    # InfiniBand support
    if ec.name in IB_MODULE_SOFTWARE:
        # remove any OS dependency on libverbs in non-IB nodes
        if LOCAL_ARCH_SUFFIX != IB_MODULE_SUFFIX:
            pkg_ibverbs = EASYCONFIG_CONSTANTS['OS_PKG_IBVERBS_DEV'][0]
            ec['osdependencies'] = [d for d in ec['osdependencies'] if d != pkg_ibverbs]
            ec.log.info("[parse hook] Removed IB from OS dependencies on non-IB system: %s", ec['osdependencies'])

    # OpenFabrics support
    if ec.name == 'OpenMPI':
        # remove libfabric from OpenMPI on all partitions
        ec['dependencies'] = [d for d in ec['dependencies'] if 'libfabric' not in d]
        ec.log.info("[parse hook] Removed libfabric from dependency list")

    if ec.name == 'NVHPC':
        # NVHPC ships with OpenMPI v4 which has an issue between its hwloc
        # and Slurm cgroups2 that results in mpirun trying to use unallocated
        # cores to the job (see https://github.com/open-mpi/ompi/issues/12470)
        # Only mpirun is affected, workaround is to set '--bind-to=none':
        ec.log.info("[parse hook] Disable mpirun process binding in NVHPC")
        ec['modextravars'].update({'OMPI_MCA_hwloc_base_binding_policy': 'none'})

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

    group = get_group(ec.name, ec.version)
    if group:
        ec['group'] = group
        ec.log.info(f"[parse hook] Set parameter group: {ec['group']}")

    # set optarch for intel compilers on AMD nodes
    optarchs_intel = {
        'zen2': '-march=core-avx2',
        # common-avx512 gives test failure for scipy
        # see https://github.com/easybuilders/easybuild-easyconfigs/pull/18875
        'zen4': '-march=rocketlake',
        'zen5': '-march=rocketlake',
    }
    if LOCAL_ARCH in optarchs_intel and ec.toolchain.name in ['intel-compilers', 'iimpi', 'iimkl', 'intel']:
        optarch = ec.toolchain.options.get('optarch')
        # only set if not set in the easyconfig or if set to default value (i.e. True)
        if not optarch or optarch is True:
            ec.toolchain.options['optarch'] = optarchs_intel[LOCAL_ARCH]
            ec.log.info(f"[parse hook] Set optarch in parameter toolchainopts: {ec.toolchain.options['optarch']}")

    ###############################
    # ------ GPU MODULES -------- #
    ###############################

    # skip installation of CUDA software in non-GPU architectures, only create a dummy module file
    if is_gpu_software(ec) and LOCAL_ARCH_FULL not in GPU_ARCHS:
        ec.log.info("[parse hook] Generating dummy GPU module on non-GPU node")
        # remove all dependencies to avoid unnecessary module loads on the dummy module
        ec['dependencies'] = []
        # inject error message in module file
        ec['modluafooter'] = GPU_DUMMY_MOD_FOOTER
        # workaround for NVHPC
        if ec.name == 'NVHPC':
            ec['default_cuda_version'] = '0'
        # module_only steps: [MODULE_STEP, PREPARE_STEP, READY_STEP, POSTITER_STEP, SANITYCHECK_STEP]
        ec['module_only'] = True
        ec.log.info(f"[parse hook] Set parameter module_only: {ec['module_only']}")
        ec['skipsteps'] = [SANITYCHECK_STEP]
        ec.log.info(f"[parse hook] Set parameter skipsteps: {ec['skipsteps']}")

    # set cuda compute capabilities
    elif is_gpu_software(ec):
        # on GPU nodes set cuda compute capabilities
        ec['cuda_compute_capabilities'] = ARCHS[LOCAL_ARCH_FULL]['cuda_cc']
        ec.log.info(f"[parse hook] Set parameter cuda_compute_capabilities: {ec['cuda_compute_capabilities']}")


def pre_fetch_hook(self):
    """Hook at pre-fetch level"""
    acquire_fetch_lock(self)


def post_fetch_hook(self):
    """Hook at post-fetch level"""
    release_fetch_lock(self)


def pre_configure_hook(self, *args, **kwargs):  # pylint: disable=unused-argument
    """Hook at pre-configure level to alter configopts"""

    # don’t remove installdir when installing with Tarball easyblock for bwrap (only for the vsc bot)
    if os.getenv('BWRAP', '') == '1' and 'install_type' in self.cfg:
        self.cfg['install_type'] = 'merge'
        self.log.info("[pre-configure hook] Set install_type to %s for bwrap", self.cfg['install_type'])

    # BLIS autodetection fails on zen5, set to zen3 (the highest currently supported zen)
    if self.name == 'BLIS' and LOCAL_ARCH == 'zen5' and LooseVersion(self.version) <= LooseVersion('2.0'):
        self.cfg['cpu_architecture'] = 'zen3'

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
        ec_param = IB_MODULE_SOFTWARE[self.name][0]

        # convert any non-list parameters to a list
        if ec_param == 'configopts':
            ec_config = self.cfg['configopts'].split(' ')
        else:
            ec_config = self.cfg[ec_param]

        # clean any settings about IB
        ib_free_config = [opt for opt in ec_config if not any(mark in opt for mark in IB_OPT_MARK)]

        # update IB settings
        if LOCAL_ARCH_SUFFIX == IB_MODULE_SUFFIX:
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
    """
    Hook at pre-module level to alter module files
    WARNING: this hooks triggers *after* sanity checks
    """

    # Must be done this way, updating self.cfg['modextravars']
    # directly doesn't work due to templating.
    with self.cfg.disable_templating():

        ##########################
        # ------ MPI ----------- #
        ##########################

        if self.name == 'OpenMPI':
            # set MPI communication type in Slurm (default is none)
            # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/4706
            slurm_mpi_type = 'pmix'

            if slurm_mpi_type:
                self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
                self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

        if self.name == 'impi':
            # - use PMI2 implementation from Slurm
            # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7192
            # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7588

            # Intel MPI supports PMI2 with I_MPI_PMI=pmi2 since v2019.7
            # see https://bugs.schedmd.com/show_bug.cgi?id=6727
            slurm_mpi_type = 'pmi2'
            intel_mpi = {
                'pmi_set': 'pmi2',
                'pmi_lib': '/usr/lib64/slurmpmi/libpmi2.so',
            }

            self.log.info("[pre-module hook] Set MPI bootstrap for Slurm")
            self.cfg['modluafooter'] = INTEL_MPI_MOD_FOOTER.format(**intel_mpi)

            if slurm_mpi_type:
                self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
                self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

        if self.name in ['ANSYS', 'FLUENT']:
            # ANSYS versions 2022+ use Intel MPI v2021 by default
            # do not set SLURM_MPI_TYPE as ANSYS has both OpenMPI and Intel MPI implementations
            # both work well on their own without an explicit SLURM_MPI_TYPE
            ansys_intel_mpi = {
                'pmi_set': 'pmi2',
                'pmi_lib': '/usr/lib64/slurmpmi/libpmi2.so',
            }
            self.log.info("[pre-module hook] Set MPI bootstrap for Slurm")
            self.cfg['modluafooter'] = INTEL_MPI_MOD_FOOTER.format(**ansys_intel_mpi)
            # remove restrictions on UCX transport layer, IB 'dc' not supported at system level
            self.log.info("[pre-module hook] Allow all trasnports in UCX for ANSYS")
            self.cfg['modextravars'].update({'UCX_TLS': "all"})
            # the following mimics what ANSYS FLUENT does when it uses its integrated slurm capabilities
            # with command: `fluent 2dpp -scheduler=slurm -t2 --mpi=openmpi -mpitest`
            # see: https://ansyshelp.ansys.com/public//Views/Secured/corp/v242/en/flu_lm/slurm-140005.1.html
            self.log.info("[pre-module hook] Enabling Slurm integration in ANSYS")
            self.cfg['modextravars'].update({'SLURM_ENABLED': "1"})
            self.cfg['modextravars'].update({'SCHEDULER_TIGHT_COUPLING': "1"})

        if self.name == 'NVHPC':
            slurm_mpi_type = 'pmix'
            self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
            self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

        ##########################
        # ------ TUNING -------- #
        ##########################

        if self.name == 'Java':
            # set the maximum heap memory for Java applications to 80% of memory allocated to the job
            # more info: https://projects.cc.vub.ac.be/issues/2940
            self.log.info("[pre-module hook] Set max heap memory in Java module")
            self.cfg['modluafooter'] = JAVA_MOD_FOOTER

        # set MATLAB Runtime Component Cache folder to a local temp dir
        # this cache directory lies in $HOME by default, which cause binaries compiled with MCC to hang
        if self.name == 'MATLAB':
            self.log.info("[pre-module hook] Set MATLAB Runtime Component Cache folder")
            self.cfg['modluafooter'] = """
setenv("MCR_CACHE_ROOT", os.getenv("TMPDIR") or pathJoin("/tmp", os.getenv("USER")))
"""

        ##########################
        # ------ LICENSES ------ #
        ##########################

        # set COMSOL licenses
        if self.name == 'COMSOL':
            self.cfg['modluafooter'] = """
if userInGroup("bcomsol") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License.dat")
elseif userInGroup("bcomsol_efremov") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License_efremov.dat")
end
"""

        # Morfeo license file
        if self.name == 'Morfeo':
            self.cfg['modextravars'].update({'CENAERO_LICENSE_FILE': '/apps/brussel/licenses/morfeo/license.lic'})

        # ABAQUS license file
        if self.name == 'ABAQUS':
            self.cfg['modextravars'].update({'ABAQUSLM_LICENSE_FILE': '/apps/brussel/licenses/abaqus/license.lic'})

        # FreeSurfer per-user licenses
        if self.name == 'FreeSurfer':
            self.cfg['modluafooter'] = """
local username = os.getenv("USER") or ""
local licfile = pathJoin("/apps/brussel/licenses/freesurfer", username .. ".lic")
if not isFile(licfile) then
    LmodError("FreeSurfer license file not found for your VSC user. Please contact hpc@vub.be on how to obtain one.")
end
setenv("FS_LICENSE", licfile)
"""

        ##########################
        # ------ DATABASES ----- #
        ##########################

        apps_with_dbs = ["AlphaFold", "BUSCO", "ColabFold", "OpenFold"]

        if self.name in apps_with_dbs:
            self.cfg['modloadmsg'] = "%(name)s databases are located in /databases/bio/%(namelower)s-%(version)s"

        if self.name == 'BUSCO':
            if LooseVersion(self.version) >= '5.0.0':
                self.cfg['modloadmsg'] += """
Use local DBs with command: `busco --offline --download_path /databases/bio/BUSCO-5 ...`
"""

        if self.name == 'AlphaFold':
            self.cfg['modextravars'] = {
                'ALPHAFOLD_DATA_DIR': '/databases/bio/%(namelower)s-%(version)s',
            }

        # add links to our documentation for software covered in
        # https://hpc.vub.be/docs/software/usecases/
        doc_url = 'https://hpc.vub.be/docs/software/usecases/'
        doc_app = ['MATLAB', 'R', 'Gaussian', 'GaussView', 'matplotlib', ('CESM-deps', 'cesm-cime'), 'GAP',
                   'Mathematica', 'Stata', 'GROMACS', 'CP2K', 'PyTorch', 'ORCA', 'SRA-Toolkit', 'AlphaFold',
                   'OpenFold', 'GAMESS-US']

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


def post_build_and_install_loop_hook(ecs_with_res):
    """
    Hook to run after all easyconfigs have been built and installed

    :param ecs_with_res: list of easyconfig tuples, where each tuple consists of 2 dicts:
                         the easyconfig data and the build status data.
    """

    installed_modules = [x[0]['full_mod_name'] for x in ecs_with_res if x[1]['success']]
    if installed_modules:
        sys.stderr.write(f'BUILD_TOOLS: builds_succeeded {" ".join(installed_modules)}\n')
