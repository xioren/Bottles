# vulkan.py
#
# Copyright 2022 brombinmirko <send@mirko.pm>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import shutil
import filecmp
import subprocess

from glob import glob
from collections import defaultdict

FALLBACK_VULKAN_DATA_DIRS = [
    "/usr/local/etc",  # standard site-local location
    "/usr/local/share",  # standard site-local location
    "/etc",  # standard location
    "/usr/share",  # standard location
    "/usr/lib/x86_64-linux-gnu/GL",  # Flatpak GL extension
    "/usr/lib/i386-linux-gnu/GL",  # Flatpak GL32 extension
    "/opt/amdgpu-pro/etc"  # AMD GPU Pro - TkG
]


class VulkanUtils:
    # NOTE: borrows heavily from https://github.com/lutris/lutris/blob/master/lutris/util/system.py
    def __init__(self):
        self.loaders = self.__get_vk_icd_loaders()

    def __get_vk_icd_files(self):
        all_icd_search_paths = []
        
        def add_icd_search_path(paths):
            if paths:
                # unixy env vars with multiple paths are : delimited
                for path in paths.split(":"):
                    path = os.path.join(path, "vulkan")
                    if os.path.exists(path) and path not in all_icd_search_paths:
                        all_icd_search_paths.append(path)

        # Must match behavior of
        # https://github.com/KhronosGroup/Vulkan-Loader/blob/v1.3.235/docs/LoaderDriverInterface.md#driver-discovery-on-linux
        # (or a newer version of the same standard)

        # 1.a XDG_CONFIG_HOME or ~/.config if unset
        add_icd_search_path(os.getenv("XDG_CONFIG_HOME") or os.path.join(os.getenv("HOME"), "/.config"))
        # 1.b XDG_CONFIG_DIRS
        add_icd_search_path(os.getenv("XDG_CONFIG_DIRS") or "/etc/xdg")

        # 2, 3 SYSCONFDIR and EXTRASYSCONFDIR
        # Compiled in default has both the same
        add_icd_search_path("/etc")

        # 4 XDG_DATA_HOME
        add_icd_search_path(os.getenv("XDG_DATA_HOME") or (os.path.join(os.getenv("HOME"), ".local/share")))

        # 5 XDG_DATA_DIRS or fall back to /usr/local/share and /usr/share
        add_icd_search_path(os.getenv("XDG_DATA_DIRS") or "/usr/local/share:/usr/share")

        # FALLBACK
        # dirs that aren't from the loader spec are searched last
        for fallback_dir in FALLBACK_VULKAN_DATA_DIRS:
            add_icd_search_path(fallback_dir)

        all_icd_files = []

        for data_dir in all_icd_search_paths:
            path = os.path.join(data_dir, "icd.d", "*.json")
            # sort here as directory enumeration order is not guaranteed in linux
            # so it's consistent every time
            icd_files = sorted(glob(path))
            if icd_files:
                all_icd_files += icd_files

        return all_icd_files

    def __get_vk_icd_loaders(self):
        loaders = defaultdict(list)
        all_icd_files = self.__get_vk_icd_files()
    
        # Add loaders for each vendor
        for loader in all_icd_files:
            if "intel" in loader:
                loaders["intel"].append(loader)
            elif "radeon" in loader:
                loaders["amdradv"].append(loader)
            elif "nvidia" in loader:
                loaders["nvidia"].append(loader)
            elif "amd" in loader:
                if "pro" in loader:
                    loaders["amdvlkpro"].append(loader)
                else:
                    loaders["amdvlk"].append(loader)
            else:
                loaders["unknown"].append(loader)
    
        return loaders

    def get_vk_icd(self, vendor: str, as_string=False):
        vendors = [
            "amd",
            "amdradv",
            "amdvlk",
            "amdvlkpro",
            "nvidia",
            "intel"
            "unknown"
        ]
        icd = []

        if vendor in vendors:
            icd = self.loaders.get(vendor, "")

        if icd and as_string:
            icd = ":".join(icd)

        return icd

    @staticmethod
    def check_support():
        return True

    @staticmethod
    def test_vulkan():
        if shutil.which("vulkaninfo") is None:
            return "vulkaninfo tool not found"

        res = subprocess.Popen(
            "vulkaninfo",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        ).communicate()[0].decode("utf-8")

        return res
