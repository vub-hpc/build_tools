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


def acquire_fetch_lock(lockfile, log):
    """
    Acquire the fetch lock with the given lockfile

    The lock (a flufl file lock) guards a resource against concurrent
    access (e.g. a software source directory against concurrent
    fetches). It is released by release_fetch_lock.
    """
    wait_time = 0
    wait_interval = 60
    wait_limit = 1800

    # the lock lifetime must be larger than wait_limit, so that a held lock
    # cannot expire while other builds are still waiting for it
    lock_lifetime = 10800

    lock_dir = os.path.dirname(lockfile)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    lock = Lock(lockfile, lifetime=lock_lifetime, default_timeout=1)
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
                error_msg = (f"[pre-fetch hook] Maximum wait time for lock {lock.lockfile} "
                             f"to be released reached: {wait_time} sec >= {wait_limit} sec")
                raise RuntimeError(error_msg) from err

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
