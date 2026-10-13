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
Helper functions to handle temp files and fetch locks

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os
import sys
import tempfile
import time

from flufl.lock import Lock, LockState, TimeOutError, NotLockedError

from easybuild.framework.easyconfig.easyconfig import letter_dir_for
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.config import source_paths
from easybuild.tools.filetools import mkdir

from build_tools import stdlib_logger

logger = stdlib_logger(__name__)


def write_tempfile(contents):
    """
    Helper function to write tmp file, it returns the actual filename
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as handle:
            handle.write(contents)
    except IOError as err:
        logger.error("Error writing tmp file: %s", err)
        sys.exit(1)

    return handle.name


def acquire_fetch_lock(name, log):
    """
    Acquire the fetch lock for the software with the given name

    The lock (a flufl file lock in <sourcepath>/.locks) guards the source
    directory of the software against concurrent fetches. It is released
    by release_fetch_lock.
    """
    source_path = source_paths()[0]
    full_source_path = os.path.join(source_path, letter_dir_for(name), name)
    lock_name = full_source_path.replace('/', '_') + '.lock'

    lock_dir = os.path.join(source_path, '.locks')
    mkdir(lock_dir, parents=True)

    wait_time = 0
    wait_interval = 60
    wait_limit = 1800

    # the lock lifetime must be larger than wait_limit, so that a held lock
    # cannot expire while other builds are still waiting for it
    lock_lifetime = 10800

    lock = Lock(os.path.join(lock_dir, lock_name), lifetime=lock_lifetime, default_timeout=1)
    log.debug("[pre-fetch hook] Acquiring lock %s", lock.lockfile)

    while True:
        try:
            # try to acquire the lock
            lock.lock()
            log.info("[pre-fetch hook] Lock acquired: %s", lock.lockfile)
            return lock

        except TimeOutError as err:
            if lock.state == LockState.stale:
                # flufl only reports stale when the lock was taken on this
                # host and the holder process is no longer running there
                # (e.g. its job was killed). Locks taken on other hosts
                # report unknown and are never broken here; they expire
                # after the lock lifetime instead
                # break the stale lock and try again
                log.info("[pre-fetch hook] Lock %s is stale (holder no longer running), breaking it",
                         lock.lockfile)
                try:
                    os.remove(lock.lockfile)
                except FileNotFoundError:
                    # another build already broke the stale lock
                    pass
                continue

            if wait_time >= wait_limit:
                error_msg = "[pre-fetch hook] Maximum wait time for lock %s to be released reached: %s sec >= %s sec"
                raise EasyBuildError(error_msg, lock.lockfile, wait_time, wait_limit) from err

            msg = "[pre-fetch hook] Lock %s held by another build, waiting %d seconds..."
            log.debug(msg, lock.lockfile, wait_interval)
            time.sleep(wait_interval)
            wait_time += wait_interval


def release_fetch_lock(lock, log):
    """
    Release the fetch lock acquired by acquire_fetch_lock
    """
    try:
        lock.unlock()
        log.info("[post-fetch hook] Lock released: %s", lock.lockfile)

    except NotLockedError:
        log.warning("[post-fetch hook] Could not release lock %s: was already released", lock.lockfile)
