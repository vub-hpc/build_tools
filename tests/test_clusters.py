#
# Copyright 2017-2026 Vrije Universiteit Brussel
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
Unit tests for build_tools.clusters

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import re
import subprocess
import sys

from build_tools import clusters


def _import_clusters(rootdir, cluster_env=None):
    """Import build_tools.clusters in a fresh interpreter

    The module reads VSC_INSTITUTE_CLUSTER at import time, so each
    scenario needs its own interpreter.
    """
    env = os.environ.copy()
    env.pop('VSC_INSTITUTE_CLUSTER', None)
    if cluster_env is not None:
        env['VSC_INSTITUTE_CLUSTER'] = cluster_env
    env['PYTHONPATH'] = os.path.join(rootdir, '..', 'src')
    code = "from build_tools import clusters; print(clusters.MACHINE)"
    return subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env)


def test_import_without_cluster_env_exits(rootdir):
    result = _import_clusters(rootdir)

    assert result.returncode == 1
    assert "VSC_INSTITUTE_CLUSTER environment variable is undefined" in result.stderr


def test_machine_sofia(rootdir):
    result = _import_clusters(rootdir, cluster_env='sofia')

    assert result.returncode == 0
    assert result.stdout.strip() == 'sofia'

    result = _import_clusters(rootdir, cluster_env='hydra')

    assert result.returncode == 0
    assert result.stdout.strip() == 'brussel'


def test_partitions_configuration():
    # every partition must define the keys used by submit_build.py and lmodtools.py
    required_keys = {'cluster', 'arch', 'long_walltime', 'nodes', 'tasks', 'gpus'}
    for partition, props in clusters.PARTITIONS.items():
        assert required_keys <= props.keys(), f"partition {partition} is missing keys"
        assert props['cluster'] in (clusters.ANANSI, clusters.HYDRA, clusters.MANTICORE, clusters.SOFIA)
        assert isinstance(props['arch'], str) and props['arch']
        assert re.fullmatch(r'\d+:\d+:\d+', props['long_walltime'])
        assert isinstance(props['nodes'], int) and props['nodes'] >= 1
        assert isinstance(props['tasks'], int) and props['tasks'] >= 1
        assert isinstance(props['gpus'], str)


def test_archs_configuration():
    # every arch must define the keys used by submit_build.py, hooks_hydra.py and lmodtools.py
    for machine in (clusters.BRUSSEL, clusters.SOFIA):
        assert machine in clusters.ARCHS, f"machine {machine} is missing from ARCHS"
        for arch, props in clusters.ARCHS[machine].items():
            assert {'default', 'partition'} <= props.keys(), f"arch {arch} of {machine} is missing keys"
            assert isinstance(props['default'], bool)
            assert {'cpu', 'gpu'} <= props['partition'].keys()
            for kind in ('cpu', 'gpu'):
                partition = props['partition'][kind]
                if partition is not None:
                    assert isinstance(partition, str)
                    # the partition must exist and point back to this arch
                    assert partition in clusters.PARTITIONS
                    assert clusters.PARTITIONS[partition]['arch'] == arch
            # every arch has a CPU partition
            assert props['partition']['cpu'] is not None
            if props['partition']['gpu'] is not None:
                # GPU archs must define the CUDA compute capabilities (used by hooks_hydra)
                assert 'cuda_cc' in props, f"GPU arch {arch} of {machine} is missing cuda_cc"
                cuda_cc = props['cuda_cc']
                assert isinstance(cuda_cc, list) and cuda_cc
                assert all(re.fullmatch(r'\d+\.\d+', cc) for cc in cuda_cc)
            if 'lmod_json_spider_cache' in props:
                assert props['lmod_json_spider_cache'] in ('0', '1')
